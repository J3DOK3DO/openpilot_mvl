"""Static and fail-closed tests for the C17 display-only host bench."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
DRIVER = TOOLS / "c17_standalone_ui.py"
PUBLISHER = TOOLS / "c17_device_state_publisher.py"
LAUNCHER = TOOLS / "c17_standalone_ui.sh"
REDIRECT = TOOLS / "c17_ipc_redirect.c"


def build_redirect(root: Path) -> Path:
  library = root / "redirect.so"
  subprocess.run(["cc", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
                  str(REDIRECT), "-ldl", "-o", str(library)], check=True)
  return library


def run_preloaded(library: Path, root: Path, script: str) -> dict:
  env = os.environ.copy()
  env.update({"LD_PRELOAD": str(library), "C17_MSGQ_ROOT": str(root),
              "OPENPILOT_PREFIX": "c17_regression"})
  proc = subprocess.run(["python3", "-c", script], env=env, text=True,
                        capture_output=True, check=True)
  return json.loads(proc.stdout)


class TestC17Safety(unittest.TestCase):
  def test_only_device_state_pubmaster(self):
    calls = []
    for path in (DRIVER, PUBLISHER):
      tree = ast.parse(path.read_text(), filename=str(path))
      for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "PubMaster":
          calls.append((path.name, ast.literal_eval(node.args[0])))
    self.assertEqual(calls, [(PUBLISHER.name, ["deviceState"])])

  def test_publisher_send_is_literal_device_state(self):
    tree = ast.parse(PUBLISHER.read_text(), filename=str(PUBLISHER))
    sends = [node for node in ast.walk(tree)
             if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "send"]
    self.assertEqual(len(sends), 1)
    self.assertEqual(ast.literal_eval(sends[0].args[0]), "deviceState")

  def test_no_vehicle_or_manager_imports(self):
    forbidden = ("manager", "modeld", "radard", "plannerd", "pandad")
    imports = []
    for path in (DRIVER, PUBLISHER):
      for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
          imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
          imports.append(node.module or "")
    for module in imports:
      self.assertFalse(any(token in module.split(".") for token in forbidden), module)
    self.assertNotIn("carControl", DRIVER.read_text() + PUBLISHER.read_text())

  def test_launcher_disables_x11_tcp_and_recording(self):
    text = LAUNCHER.read_text()
    self.assertIn("-nolisten tcp", text)
    self.assertIn("RECORD=0", text)
    self.assertIn("LIBGL_ALWAYS_SOFTWARE=1", text)
    self.assertIn("C17_MSGQ_ROOT=$RUNTIME_DIR/msgq", text)
    self.assertNotIn("/dev/shm", text)

  def test_redirect_shim_compiles_cleanly(self):
    with tempfile.TemporaryDirectory() as tmp:
      build_redirect(Path(tmp))

  def test_redirect_legitimate_native_names(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp).resolve()
      root = base / "private"
      namespace = root / "msgq_c17_regression"
      namespace.mkdir(parents=True)
      (root / "event").mkdir()
      library = build_redirect(base)
      result = run_preloaded(library, root, r'''
import ctypes, json, os
libc = ctypes.CDLL(None, use_errno=True)
fd = libc.open(b"/dev/shm/msgq_c17_regression/deviceState", os.O_CREAT | os.O_RDWR, 0o600)
open_errno = ctypes.get_errno()
if fd >= 0: os.close(fd)
shm_fd = libc.shm_open(b"/msgq_0123456789abcdef", os.O_CREAT | os.O_RDWR, 0o600)
shm_errno = ctypes.get_errno()
if shm_fd >= 0: os.close(shm_fd)
unlink_result = libc.shm_unlink(b"/msgq_0123456789abcdef")
print(json.dumps({"open_fd": fd, "open_errno": open_errno, "shm_fd": shm_fd,
                  "shm_errno": shm_errno, "unlink_result": unlink_result}))
''')
      self.assertGreaterEqual(result["open_fd"], 0)
      self.assertGreaterEqual(result["shm_fd"], 0)
      self.assertEqual(result["unlink_result"], 0)
      self.assertTrue((namespace / "deviceState").is_file())
      self.assertFalse((root / "event" / "msgq_0123456789abcdef").exists())

  def test_redirect_traversal_canaries_always_survive(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp).resolve()
      root = base / "private"
      (root / "msgq_c17_regression").mkdir(parents=True)
      (root / "event").mkdir()
      library = build_redirect(base)
      for operation, call in (
        ("open", 'libc.open(b"/dev/shm/msgq_c17_regression/../../../victim", os.O_WRONLY | os.O_TRUNC, 0)'),
        ("open64", 'libc.open64(b"/dev/shm/msgq_c17_regression/../../../victim", os.O_WRONLY | os.O_TRUNC, 0)'),
        ("shm_unlink", 'libc.shm_unlink(b"/msgq_/../../../victim")'),
      ):
        with self.subTest(operation=operation):
          victim = base / "victim"
          victim.write_text("C17_CANARY_MUST_SURVIVE")
          result = run_preloaded(library, root, f'''
import ctypes, json, os
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
ret = {call}
print(json.dumps({{"return": ret, "errno": ctypes.get_errno()}}))
''')
          self.assertEqual(result, {"return": -1, "errno": 22})
          self.assertEqual(victim.read_text(), "C17_CANARY_MUST_SURVIVE")

  def test_redirect_rejects_invalid_shm_names_without_fallback(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp).resolve()
      root = base / "private"
      root.mkdir()
      library = build_redirect(base)
      for name in (b"/msgq_", b"/msgq_.", b"/msgq_..", b"/msgq_a/b", b"/msgq_a\\b"):
        with self.subTest(name=name):
          result = run_preloaded(library, root, f'''
import ctypes, json
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
ret = libc.shm_open({name!r}, 0, 0)
print(json.dumps({{"return": ret, "errno": ctypes.get_errno()}}))
''')
          self.assertEqual(result, {"return": -1, "errno": 22})

  def test_redirect_rejects_symlink_root(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp).resolve()
      actual = base / "actual"
      actual.mkdir()
      root = base / "private"
      root.symlink_to(actual, target_is_directory=True)
      library = build_redirect(base)
      result = run_preloaded(library, root, r'''
import ctypes, json, os
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
ret = libc.shm_open(b"/msgq_0123456789abcdef", os.O_CREAT | os.O_RDWR, 0o600)
print(json.dumps({"return": ret, "errno": ctypes.get_errno()}))
''')
      self.assertEqual(result, {"return": -1, "errno": 22})
      self.assertEqual(list(actual.iterdir()), [])

  def test_redirect_rejects_symlink_child_directories(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp).resolve()
      root = base / "private"
      outside = base / "outside"
      root.mkdir()
      outside.mkdir()
      (root / "event").symlink_to(outside, target_is_directory=True)
      (root / "msgq_c17_regression").symlink_to(outside, target_is_directory=True)
      library = build_redirect(base)
      result = run_preloaded(library, root, r'''
import ctypes, json, os
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
shm_ret = libc.shm_open(b"/msgq_0123456789abcdef", os.O_CREAT | os.O_RDWR, 0o600)
shm_errno = ctypes.get_errno()
ctypes.set_errno(0)
open_ret = libc.open(b"/dev/shm/msgq_c17_regression/deviceState", os.O_CREAT | os.O_RDWR, 0o600)
open_errno = ctypes.get_errno()
print(json.dumps({"shm_return": shm_ret, "shm_errno": shm_errno,
                  "open_return": open_ret, "open_errno": open_errno}))
''')
      self.assertEqual(result, {"shm_return": -1, "shm_errno": 22,
                                "open_return": -1, "open_errno": 22})
      self.assertEqual(list(outside.iterdir()), [])

  def test_wrong_source_fails_before_graphics(self):
    with tempfile.TemporaryDirectory() as tmp:
      proc = subprocess.run([str(LAUNCHER), "--layout", "compact", "--output", tmp],
                            env={"C17_SOURCE_ROOT": tmp, "PATH": "/usr/bin:/bin"},
                            text=True, capture_output=True)
    self.assertEqual(proc.returncode, 69)
    self.assertIn("pinned host runtime unavailable", proc.stderr)

  def test_missing_xvfb_fails_closed(self):
    with tempfile.TemporaryDirectory() as tmp:
      proc = subprocess.run([str(LAUNCHER), "--layout", "compact", "--output", tmp],
                            env={"C17_XVFB_BIN": "/nonexistent/c17-xvfb", "PATH": "/usr/bin:/bin"},
                            text=True, capture_output=True)
    self.assertEqual(proc.returncode, 69)
    self.assertIn("Xvfb unavailable", proc.stderr)

  def test_existing_output_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      (Path(tmp) / "ui.log").write_text("preserve")
      proc = subprocess.run([str(LAUNCHER), "--layout", "compact", "--output", tmp],
                            text=True, capture_output=True)
      self.assertEqual(proc.returncode, 73)
      self.assertEqual((Path(tmp) / "ui.log").read_text(), "preserve")


if __name__ == "__main__":
  unittest.main()
