"""Safety, ABI, integrity, and lifecycle contract tests for Campaign 18."""
from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
ENTRY = TOOLS / "c18_native_ui.py"
LAUNCHER = TOOLS / "c18_native_ui.sh"
PREFLIGHT_PATH = TOOLS / "c18_preflight.py"
BUILD_PATH = TOOLS / "c18_build_package.py"
SUPERVISOR = TOOLS / "c18_supervise.sh"


def load(name: str, path: Path):
  spec = importlib.util.spec_from_file_location(name, path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


PREFLIGHT = load("c18_preflight_test", PREFLIGHT_PATH)
BUILD = load("c18_build_test", BUILD_PATH)


class TestC18NativeUI(unittest.TestCase):
  def test_entrypoint_never_publishes(self):
    tree = ast.parse(ENTRY.read_text())
    calls = [getattr(node.func, "attr", "") for node in ast.walk(tree)
             if isinstance(node, ast.Call)]
    self.assertNotIn("PubMaster", calls)
    self.assertNotIn("send", calls)

  def test_entrypoint_has_no_control_or_manager_imports(self):
    tree = ast.parse(ENTRY.read_text())
    modules = []
    for node in ast.walk(tree):
      if isinstance(node, ast.Import):
        modules.extend(alias.name for alias in node.names)
      elif isinstance(node, ast.ImportFrom):
        modules.append(node.module or "")
    forbidden = {"manager", "controls", "modeld", "plannerd", "radard", "pandad", "boardd"}
    for module in modules:
      self.assertFalse(forbidden & set(module.split(".")), module)

  def test_launcher_requires_all_physical_gates_and_no_preload(self):
    text = LAUNCHER.read_text()
    for marker in ("physical_isolation_verified", "device_identity_verified",
                   "power_thermal_verified", "backup_verified", "recovery_demonstrated",
                   "independent_test_approval", "installation_authorized", "manifest_sha256",
                   "c18-device-authorization-v1", "0:400"):
      self.assertIn(marker, text)
    self.assertIn("unset HTTP_PROXY", text)
    self.assertIn('"$PYTHON" -P', text)
    self.assertNotIn('exec "$PYTHON"', text)
    self.assertIn("c18_supervise", text)
    self.assertIn("LD_PRELOAD", text)
    self.assertNotIn("c17_ipc_redirect", text)

  def test_supervisor_term_reaps_child_and_removes_runtime(self):
    with tempfile.TemporaryDirectory(dir="/tmp", prefix="c18-supervisor-test.") as outer:
      outer_path = Path(outer)
      runtime = Path(tempfile.mkdtemp(dir="/tmp", prefix="c18-display."))
      pidfile = outer_path / "child.pid"
      marker = outer_path / "child.term"
      child = (f'trap "sleep 0.2; echo handled > {marker}; exit 0" TERM; '
               f'echo $$ > {pidfile}; while :; do sleep 1; done')
      command = ["bash", "-c", f'source "{SUPERVISOR}"; c18_supervise "{runtime}" bash -c "$1"',
                 "supervisor-test", child]
      proc = subprocess.Popen(command)
      for _ in range(100):
        if pidfile.exists():
          break
        time.sleep(0.01)
      self.assertTrue(pidfile.exists())
      child_pid = int(pidfile.read_text())
      proc.send_signal(signal.SIGTERM)
      proc.wait(timeout=5)
      self.assertTrue(marker.exists())
      self.assertFalse(runtime.exists())
      with self.assertRaises(ProcessLookupError):
        os.kill(child_pid, 0)

  def test_launcher_refuses_non_target_before_authorization(self):
    with tempfile.TemporaryDirectory() as temporary:
      status = str(Path(temporary) / "status.json")
      proc = subprocess.run([str(LAUNCHER), "--status", status,
                             "--authorization", str(Path(temporary) / "missing.json")],
                            text=True, capture_output=True)
    self.assertEqual(proc.returncode, 69)
    self.assertIn("requires physical AGNOS 19.9 AArch64", proc.stderr)

  def test_source_closure_is_pinned_and_no_controller_binaries(self):
    files = BUILD.source_closure()
    self.assertIn("openpilot/selfdrive/ui/layouts/main.py", files)
    self.assertIn("openpilot/selfdrive/assets/fonts/Inter-Regular.ttf", files)
    self.assertTrue(any(name.startswith("opendbc_repo/opendbc/car/") and name.endswith(".capnp")
                        for name in files))
    binary_suffixes = (".so", ".a", ".o", ".onnx", ".dlc")
    self.assertFalse([name for name in files if name.endswith(binary_suffixes)])
    self.assertFalse([name for name in files
                      if Path(name).name.lower() in {"id_rsa", "id_dsa"}
                      or Path(name).suffix.lower() in {".pem", ".key", ".p12", ".pfx"}])

  def test_source_closure_follows_relative_imports(self):
    files = BUILD.source_closure()
    self.assertIn("openpilot/sunnypilot/starpilot_bridge/adapter.py", files)
    self.assertIn("openpilot/sunnypilot/starpilot_bridge/models.py", files)

  def test_relative_import_resolution_from_package_and_module(self):
    package_node = ast.parse("from .adapter import ReadOnlyStatusAdapter").body[0]
    module_node = ast.parse("from ..models import BridgeSnapshot").body[0]
    self.assertIn("openpilot.sunnypilot.starpilot_bridge.adapter",
                  BUILD.imported_modules(package_node,
                    "openpilot/sunnypilot/starpilot_bridge/__init__.py"))
    self.assertIn("openpilot.sunnypilot.starpilot_bridge.models",
                  BUILD.imported_modules(module_node,
                    "openpilot/sunnypilot/starpilot_bridge/sub/module.py"))

  def test_authentic_arm64_dependency_audit(self):
    _entries, audit = BUILD.collect_entries()
    self.assertEqual(len(audit["native_binaries"]), 3)
    self.assertTrue(all(item["abi"] == "aarch64" for item in audit["native_binaries"]))
    self.assertEqual(audit["publisher_services"], [])
    self.assertFalse(audit["ld_preload_used"])

  def test_manifest_records_exact_release_engineering_commit(self):
    with tempfile.TemporaryDirectory() as temporary:
      release_commit = "a" * 40
      manifest, _verification = BUILD.build(Path(temporary) / "candidate.tar.gz", release_commit)
    self.assertEqual(manifest["release_engineering_commit"], release_commit)

  def test_reference_rootfs_has_authentic_comma_graphics_closure(self):
    result = PREFLIGHT.validate_rootfs(Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs"))
    needed = set(result["raylib_comma_backend"]["needed"])
    self.assertTrue({"libEGL.so.1", "libGLESv2.so.2", "libgbm.so.1", "libdrm.so.2"} <= needed)
    self.assertFalse(result["graphics_hardware_executed"])

  def test_corrupt_package_file_fails_closed(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      payload = root / "payload"
      payload.write_text("good")
      manifest = {"classification": "NATIVE_UI_OFFLINE_CANDIDATE",
                  "files": {"payload": {"sha256": "0" * 64, "bytes": 4}}}
      (root / "MANIFEST.json").write_text(json.dumps(manifest))
      with self.assertRaisesRegex(ValueError, "package file mismatch"):
        PREFLIGHT.validate_package(root)

  def test_wrong_agnos_version_fails_closed(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      (root / "VERSION").write_text("19.8\n")
      with self.assertRaisesRegex(ValueError, "AGNOS version"):
        PREFLIGHT.validate_rootfs(root)

  def test_status_write_is_atomic_and_refuses_existing_temp(self):
    entry = load("c18_entry_test", ENTRY)
    with tempfile.TemporaryDirectory() as temporary:
      output = Path(temporary) / "status.json"
      entry.write_status(output, {"ok": True})
      self.assertEqual(json.loads(output.read_text()), {"ok": True})
      output.unlink()
      output.with_name(".status.json.tmp").write_text("preserve")
      with self.assertRaises(FileExistsError):
        entry.write_status(output, {"ok": False})


if __name__ == "__main__":
  unittest.main()
