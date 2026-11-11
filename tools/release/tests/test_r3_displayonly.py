from __future__ import annotations

import ast
import hashlib
import io
import os
from pathlib import Path
import signal
import socket
import subprocess
import tarfile
import time

from tools.release import c19_clean_install_build as build


ROOT = Path(__file__).resolve().parents[3]


def _install(root: Path, payload: Path, installer: Path | None = None,
             **extra: str) -> subprocess.CompletedProcess:
  env = os.environ.copy()
  env.update({"R3_OFFLINE_INSTALL_TEST": "1", "R3_INSTALL_ROOT": str(root),
              "R3_PAYLOAD_URL": payload.as_uri()})
  env.update(extra)
  return subprocess.run(["bash", str(installer or ROOT / "installer")], env=env,
                        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)


def _installer_for_hash(tmp_path: Path, digest: str) -> Path:
  source = (ROOT / "installer").read_text()
  current = source.split('PAYLOAD_SHA256="', 1)[1].split('"', 1)[0]
  path = tmp_path / "installer"
  path.write_text(source.replace(current, digest, 1))
  return path


def test_layouts_fit_and_truthful() -> None:
  import sys
  sys.path.insert(0, str(ROOT / "displayonly"))
  import layout
  for name, expected in (("compact", (536, 240)), ("large", (2160, 1080))):
    for demo in (False, True):
      dimensions, commands = layout.commands(name, demo)
      assert dimensions == expected
      assert layout.validate(name, demo) == []
      text = " ".join(c.text for c in commands)
      assert "DISPLAY ONLY" in text and "ACTUATION DISABLED" in text
      assert ("DEMO / OFFLINE" in text) is demo
      assert not any(term in text for term in ("km/h", "mph", "steering angle", "ACC SET"))


def test_runtime_import_and_publication_closure() -> None:
  imports = set()
  for name in ("displayonly/c19_display.py", "displayonly/layout.py"):
    tree = ast.parse((ROOT / name).read_text(), filename=name)
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                for alias in node.names}
    imports |= {node.module for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module}
  assert not any(name.startswith(("openpilot", "cereal", "msgq", "opendbc", "panda", "requests"))
                 for name in imports)
  runtime = (ROOT / "displayonly/c19_display.py").read_text()
  assert "DEMO_OFFLINE" in runtime and "demo is forbidden in production" in runtime
  assert all(token not in runtime for token in ("PubMaster", "Params(", ".send("))


def test_runtime_guards_block_process_and_network() -> None:
  import sys
  sys.path.insert(0, str(ROOT / "displayonly"))
  import c19_display
  original_popen = subprocess.Popen
  original_run = subprocess.run
  original_call = subprocess.call
  original_system = os.system
  original_connect = socket.socket.connect
  try:
    c19_display.install_guards()
    try:
      subprocess.Popen(["true"])
      raise AssertionError("process launch was not blocked")
    except RuntimeError as exc:
      assert "FORBIDS_PROCESS" in str(exc)
    try:
      fake_network_socket = type("FakeSocket", (), {"family": socket.AF_INET})()
      socket.socket.connect(fake_network_socket, ("127.0.0.1", 9))
      raise AssertionError("network connect was not blocked")
    except RuntimeError as exc:
      assert "FORBIDS_NONLOCAL_NETWORK" in str(exc)
  finally:
    subprocess.Popen = original_popen
    subprocess.run = original_run
    subprocess.call = original_call
    os.system = original_system
    socket.socket.connect = original_connect


def test_payload_reproducible_manifest_and_modes(tmp_path: Path) -> None:
  one, two = tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"
  result1, result2 = build.build(one), build.build(two)
  assert one.read_bytes() == two.read_bytes()
  assert result1["archive_sha256"] == result2["archive_sha256"]
  assert result1["archive_bytes"] < 4 * 1024 * 1024
  manifest = result1["manifest"]
  assert manifest["layouts"] == {"compact": [536, 240], "large": [2160, 1080]}
  assert manifest["runtime_publishers"] == [] and manifest["manager_or_vehicle_processes"] == []
  assert manifest["demo_mode"] == "OFF_BY_DEFAULT_AND_FORBIDDEN_ON_AGNOS"


def test_clean_install_duplicate_symlink_and_existing_preserved(tmp_path: Path) -> None:
  payload = tmp_path / "payload.tar.gz"
  build.build(payload)
  installer = _installer_for_hash(tmp_path, hashlib.sha256(payload.read_bytes()).hexdigest())
  root = tmp_path / "root"
  root.mkdir()
  assert _install(root, payload, installer).returncode == 0
  marker = root / "openpilot/owner-file"
  marker.write_text("preserve")
  assert _install(root, payload, installer).returncode == 73
  assert marker.read_text() == "preserve"

  symlink_root = tmp_path / "symlink"
  symlink_root.mkdir()
  target = tmp_path / "target"
  target.mkdir()
  (symlink_root / "openpilot").symlink_to(target)
  assert _install(symlink_root, payload, installer).returncode == 73
  assert (symlink_root / "openpilot").is_symlink()


def test_failure_injection_all_transaction_stages(tmp_path: Path) -> None:
  payload = tmp_path / "payload.tar.gz"
  build.build(payload)
  installer = _installer_for_hash(tmp_path, hashlib.sha256(payload.read_bytes()).hexdigest())
  for stage, code in (("before_move", 85), ("after_move", 86), ("after_continue", 87)):
    root = tmp_path / stage
    root.mkdir()
    result = _install(root, payload, installer, R3_TEST_FAIL_STAGE=stage)
    assert result.returncode == code, result.stderr
    assert not (root / "openpilot").exists()
    assert not (root / "continue.sh").exists()
    assert not list(root.glob(".r3-*"))


def test_corrupt_partial_oversize_and_missing_identity(tmp_path: Path) -> None:
  payload = tmp_path / "payload.tar.gz"
  build.build(payload)
  good_hash = hashlib.sha256(payload.read_bytes()).hexdigest()
  installer = _installer_for_hash(tmp_path, good_hash)
  for name, data in (("corrupt", b"wrong"), ("partial", payload.read_bytes()[:50])):
    candidate = tmp_path / name
    candidate.write_bytes(data)
    root = tmp_path / f"root-{name}"
    root.mkdir()
    assert _install(root, candidate, installer).returncode == 65
    assert not (root / "openpilot").exists()

  oversize = tmp_path / "oversize"
  oversize.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
  root = tmp_path / "root-oversize"
  root.mkdir()
  result = _install(root, oversize, installer)
  assert result.returncode != 0 and "bounded installer limit" in result.stderr

  missing = subprocess.run(["bash", str(ROOT / "installer")], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
  assert missing.returncode == 69


def test_malicious_members_rejected_with_matching_pin(tmp_path: Path) -> None:
  for kind in ("traversal", "symlink", "special", "duplicate"):
    candidate = tmp_path / f"{kind}.tar.gz"
    with tarfile.open(candidate, "w:gz") as archive:
      if kind == "traversal":
        info = tarfile.TarInfo("../escape")
      elif kind == "symlink":
        info = tarfile.TarInfo("openpilot/link")
        info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
      elif kind == "special":
        info = tarfile.TarInfo("openpilot/fifo")
        info.type = tarfile.FIFOTYPE
      else:
        info = tarfile.TarInfo("openpilot/repeat")
      if kind in ("traversal", "duplicate"):
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
        if kind == "duplicate":
          archive.addfile(info, io.BytesIO(b"y"))
      else:
        archive.addfile(info)
    installer = _installer_for_hash(tmp_path, hashlib.sha256(candidate.read_bytes()).hexdigest())
    root = tmp_path / f"root-{kind}"
    root.mkdir()
    result = _install(root, candidate, installer)
    assert result.returncode != 0
    assert not (root / "openpilot").exists()


def _test_launcher(tmp_path: Path, mode: str) -> tuple[Path, dict[str, str]]:
  helper = tmp_path / "fake-python"
  helper.write_text("""#!/usr/bin/env bash
set -euo pipefail
mode=${R3_FAKE_MODE:?}
ready=
while (($#)); do
  if [[ $1 == --ready ]]; then ready=$2; shift 2; else shift; fi
done
if [[ $mode == ready ]]; then printf '{}\\n' >"$ready"; fi
trap 'exit 0' TERM INT HUP
while true; do sleep 1; done
""")
  helper.chmod(0o755)
  source = (ROOT / "displayonly/launch.sh").read_text()
  source = source.replace("PYTHON=/usr/local/venv/bin/python", f"PYTHON={helper}")
  source = source.replace(
    '[[ -x $PYTHON && -f /AGNOS && -r /VERSION && $(cat /VERSION) == 19.9 ]] || {',
    '[[ -x $PYTHON ]] || {')
  source = source.replace(
    '[[ -S /tmp/drmfd.sock && -e /dev/dri/card0 ]] || {',
    '[[ -x $PYTHON ]] || {')
  source = source.replace("if ps -eo comm= | grep -Eq", "if false && ps -eo comm= | grep -Eq")
  launcher = tmp_path / "launch.sh"
  launcher.write_text(source)
  launcher.chmod(0o755)
  return launcher, {**os.environ, "R3_FAKE_MODE": mode,
                    "R3_STARTUP_TIMEOUT_SECONDS": "1", "R3_KILL_GRACE_SECONDS": "1"}


def test_launcher_watchdog_and_signal_cleanup(tmp_path: Path) -> None:
  before = set(Path("/tmp").glob("r3-display.*"))
  launcher, env = _test_launcher(tmp_path, "hang")
  timed = subprocess.run(["bash", str(launcher)], env=env, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
  assert timed.returncode == 124 and "watchdog expired" in timed.stderr
  assert set(Path("/tmp").glob("r3-display.*")) == before

  launcher, env = _test_launcher(tmp_path, "ready")
  proc = subprocess.Popen(["bash", str(launcher)], env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  time.sleep(0.5)
  proc.send_signal(signal.SIGTERM)
  assert proc.wait(timeout=8) == 143
  assert set(Path("/tmp").glob("r3-display.*")) == before


def test_shell_syntax_and_launch_contract() -> None:
  for name in ("installer", "launch_openpilot.sh", "launch_chffrplus.sh", "displayonly/launch.sh"):
    subprocess.run(["bash", "-n", str(ROOT / name)], check=True)
  launch = (ROOT / "displayonly/launch.sh").read_text()
  assert "--demo" not in launch
  assert "setsid" in launch and "startup watchdog expired" in launch
  assert 'kill -KILL -- "-$CHILD"' in launch
