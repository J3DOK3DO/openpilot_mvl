"""C15 fail-closed evidence and path safety regression tests."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "c15_ui_bench.py"
spec = importlib.util.spec_from_file_location("c15_bench_under_test", MODULE)
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)

class TestC15BenchSafety(unittest.TestCase):
    def test_invalid_png_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"false.png"
            p.write_bytes(b"this is not a png")
            with self.assertRaises(ValueError):
                kit.png_dimensions(p)

    def test_png_dimensions_from_real_frame(self):
        p = kit.ARTIFACTS/"C15_MVL_LARGE_HOST_12FRAMES.png"
        if not p.exists():
            self.skipTest("Live C15 artifact not mounted")
        self.assertEqual(kit.png_dimensions(p), (1404, 702))

    def test_output_nested_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(kit, "ARTIFACTS", Path(tmp)):
            with self.assertRaises(ValueError):
                kit.safe_output(Path(tmp)/"nested"/"manifest.json")

    def test_output_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(kit, "ARTIFACTS", Path(tmp)):
            with self.assertRaises(ValueError):
                kit.safe_output(Path(tmp)/".."/"escape")

    def test_font_mutation_fails_closed(self):
        from unittest.mock import patch
        if not (kit.ARTIFACTS/"C15_ACTUAL_UI_LIVE_IPC.exit").exists():
            self.skipTest("Live C15 artifact not mounted")
        original = kit.sha256
        def altered(path):
            if "assets/fonts" in str(path) and str(path).startswith(str(kit.HOST_SOURCE)):
                return "0" * 64
            return original(path)
        with patch.object(kit, "sha256", side_effect=altered):
            with self.assertRaisesRegex(ValueError, "Font changed"):
                kit.evidence()

    def test_output_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp)/"realdir"
            real.mkdir()
            alias = Path(tmp)/"alias"
            alias.symlink_to(real, target_is_directory=True)
            with patch.object(kit, "ARTIFACTS", alias):
                with self.assertRaises(ValueError):
                    kit.safe_output(alias/"foo.json")

    def test_output_existing_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(kit, "ARTIFACTS", Path(tmp)):
            p = Path(tmp)/"existing.json"
            p.write_text("existing evidence")
            with self.assertRaises(ValueError):
                kit.safe_output(p)
            self.assertEqual(p.read_text(),"existing evidence")

    def test_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(kit, "ARTIFACTS", Path(tmp)):
            target=Path(tmp)/"external"
            target.write_text("protected")
            link=Path(tmp)/"symlink"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                kit.safe_output(link)
            self.assertEqual(target.read_text(),"protected")

    def test_unexpected_host_preview_publish_rejected(self):
        if not (kit.ARTIFACTS/"c15_mvl_large_loop.py").exists():
            self.skipTest("Live C15 artifact not mounted")
        original = Path.read_text
        def malicious_preview(self, *args, **kwargs):
            text = original(self, *args, **kwargs)
            if str(self).endswith("c15_mvl_large_loop.py"):
                return text + chr(10) + 'pm.send("carControl", b"bad")' + chr(10)
            return text
        with patch.object(Path, "read_text", malicious_preview):
            with self.assertRaisesRegex(ValueError, "Unexpected host preview publish"):
                kit.evidence()

    def test_missing_required_test_exit_fails_closed(self):
        with patch.object(kit, "PASS_EXIT_FILES", ("NONEXISTENT_C15_GATED_FILE.exit",)):
            with self.assertRaises(FileNotFoundError):
                kit.evidence()

    def test_actual_evidence_never_grants_install_or_actuation(self):
        if not (kit.ARTIFACTS/"C15_ACTUAL_UI_LIVE_IPC.exit").exists():
            self.skipTest("Live C15 artifact not mounted")
        data=kit.evidence()
        self.assertEqual(data["status"], "HOST_UI_BENCH_PASS_AGNOS_GPU_HARDWARE_HOLD")
        self.assertFalse(data["device_install_allowed"])
        self.assertFalse(data["actuation_allowed"])
        self.assertFalse(data["device_graphics_qualified"])
        self.assertFalse(data["g10_full_product_built"])
        self.assertEqual(data["model_artifacts_authenticated"],0)
        self.assertEqual(data["host_large_frames_rendered"],12)
        self.assertEqual(len(data["native_binaries"]),6)
        self.assertEqual(len(data["screenshots"]),2)

if __name__ == "__main__":
    unittest.main()
