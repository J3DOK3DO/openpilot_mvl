from __future__ import annotations

import ast
from pathlib import Path
import subprocess

from tools.release import c19_clean_install_build as build


ROOT = Path(__file__).resolve().parents[3]


def test_root_launchers_only_exec_display() -> None:
  for name in ("launch_openpilot.sh", "launch_chffrplus.sh"):
    text = (ROOT / name).read_text()
    assert "displayonly/launch.sh" in text
    assert all(token not in text for token in ("manager", "agnos", "abctl", "sudo", "panda"))


def test_display_has_no_ipc_params_or_vehicle_imports() -> None:
  path = ROOT / "displayonly/c19_display.py"
  tree = ast.parse(path.read_text(), filename=str(path))
  imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
             for alias in node.names}
  imports.update(node.module for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module)
  assert not any(name.startswith(("openpilot", "cereal", "msgq", "opendbc", "panda")) for name in imports)
  text = path.read_text()
  assert "DISCONNECTED" in text
  assert "ACTUATION DISABLED" in text
  assert all(token not in text for token in ("PubMaster", ".send(", "Params("))


def test_payload_is_small_and_deterministic(tmp_path: Path) -> None:
  first = tmp_path / "one.tar.gz"
  second = tmp_path / "two.tar.gz"
  one = build.build(first)
  two = build.build(second)
  assert first.read_bytes() == second.read_bytes()
  assert one["archive_sha256"] == two["archive_sha256"]
  assert one["archive_bytes"] < 1_000_000
  assert one["manifest"]["actuation_allowed"] is False


def test_shell_syntax() -> None:
  for name in ("installer", "launch_openpilot.sh", "launch_chffrplus.sh", "displayonly/launch.sh"):
    subprocess.run(["bash", "-n", str(ROOT / name)], check=True)


def _sandbox_install(root: Path, payload: Path, **extra: str) -> subprocess.CompletedProcess:
  import os
  env = os.environ.copy()
  env.update({
    "C19_OFFLINE_INSTALL_TEST": "1",
    "C19_INSTALL_ROOT": str(root),
    "C19_PAYLOAD_URL": payload.as_uri(),
  })
  env.update(extra)
  return subprocess.run(["bash", str(ROOT / "installer")], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, timeout=30)


def test_custom_installer_commit_and_duplicate_denial(tmp_path: Path) -> None:
  payload = tmp_path / "payload.tar.gz"
  build.build(payload)
  root = tmp_path / "install"
  root.mkdir()
  first = _sandbox_install(root, payload)
  assert first.returncode == 0, first.stderr
  assert (root / "openpilot/launch_openpilot.sh").is_file()
  assert (root / "openpilot/displayonly/c19_display.py").is_file()
  assert (root / "continue.sh").is_file()
  assert "exec " in (root / "continue.sh").read_text()
  repeated = _sandbox_install(root, payload)
  assert repeated.returncode == 73


def test_injected_post_move_failure_rolls_back_new_destination(tmp_path: Path) -> None:
  payload = tmp_path / "payload.tar.gz"
  build.build(payload)
  root = tmp_path / "install"
  root.mkdir()
  result = _sandbox_install(root, payload, C19_TEST_FAIL_POST_MOVE="1")
  assert result.returncode == 86, result.stderr
  assert not (root / "openpilot").exists()
  assert not (root / "continue.sh").exists()
  assert not list(root.glob(".c19-openpilot.stage.*"))
  assert not list(root.glob(".c19-payload.*"))


def test_corrupted_and_oversized_payload_are_rejected_without_install(tmp_path: Path) -> None:
  corrupted = tmp_path / "corrupted.tar.gz"
  corrupted.write_bytes(b"not the pinned payload\n")
  root1 = tmp_path / "tamper"
  root1.mkdir()
  bad = _sandbox_install(root1, corrupted)
  assert bad.returncode == 65
  assert not (root1 / "openpilot").exists() and not (root1 / "continue.sh").exists()

  oversized = tmp_path / "oversized.tar.gz"
  oversized.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
  root2 = tmp_path / "size"
  root2.mkdir()
  excess = _sandbox_install(root2, oversized)
  assert excess.returncode != 0
  assert "2 MiB" in excess.stderr
  assert not (root2 / "openpilot").exists() and not (root2 / "continue.sh").exists()


def test_existing_symlink_destination_is_rejected(tmp_path: Path) -> None:
  payload = tmp_path / "payload.tar.gz"
  build.build(payload)
  root = tmp_path / "install"
  root.mkdir()
  (root / "openpilot").symlink_to(tmp_path / "another-location")
  result = _sandbox_install(root, payload)
  assert result.returncode == 73
  assert (root / "openpilot").is_symlink()
  assert not (root / "continue.sh").exists()
