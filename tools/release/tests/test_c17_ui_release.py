"""Release sealing and source-integrity tests for C17."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "c17_ui_release.py"
SPEC = importlib.util.spec_from_file_location("c17_release_under_test", MODULE)
KIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(KIT)


class TestC17Release(unittest.TestCase):
  def test_current_runtime_audit(self):
    data = KIT.audit_runtime()
    self.assertEqual(len(data["fonts"]), 17)
    self.assertEqual(len(data["native_binaries"]), 6)
    self.assertFalse(data["device_control_publication_structurally_present"])

  def test_untrusted_host_font_fails_closed(self):
    original = KIT.sha256

    def altered(path):
      if str(path).startswith(str(KIT.HOST_SOURCE)) and "/assets/fonts/" in str(path):
        return "0" * 64
      return original(path)

    with patch.object(KIT, "sha256", side_effect=altered):
      with self.assertRaisesRegex(ValueError, "untrusted/mismatched font"):
        KIT.audit_runtime()

  def test_output_overwrite_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp).resolve()
      target = root / "sealed.json"
      target.write_text("preserve")
      with self.assertRaises(FileExistsError):
        KIT.safe_new_output(root, target.name)
      self.assertEqual(target.read_text(), "preserve")

  def test_nested_output_name_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaises(ValueError):
        KIT.safe_new_output(Path(tmp).resolve(), "nested/escape")


if __name__ == "__main__":
  unittest.main()
