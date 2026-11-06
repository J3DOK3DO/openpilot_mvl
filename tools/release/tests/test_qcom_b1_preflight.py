import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.release import qcom_b1_preflight as b1
from tools.release import qcom_b1_plan


class CapacityTests(unittest.TestCase):
    def test_unknown_peak_fails_closed_even_with_abundant_disk(self):
        self.assertEqual(b1.capacity(100 * 1024 * 1024)['decision'], 'HOLD_REQUIRED_CAPACITY_UNKNOWN')

    def test_low_disk(self):
        result = b1.capacity(1024 * 1024, outputs_scratch_tmp_peak_gib=1)
        self.assertFalse(result['arithmetic_fits'])
        self.assertEqual(result['decision'], 'HOLD_LOW_DISK')

    def test_scenario_fit_is_not_go(self):
        result = b1.capacity(10 * 1024 * 1024, outputs_scratch_tmp_peak_gib=1)
        self.assertEqual(result['decision'], 'SCENARIO_FITS_ONLY_PEAK_EVIDENCE_REQUIRED')

    def test_kib_to_gib(self):
        self.assertAlmostEqual(b1.capacity(9284868)['available_gib'], 9284868 / 1048576, places=6)

    def test_invalid_allocations(self):
        for bad in (-1, True, 100):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                b1.capacity(9284868, cache_gib=bad)

    def test_reserve_cannot_be_below_two_gib(self):
        with self.assertRaises(ValueError):
            b1.capacity(9284868, reserve_gib=1.99, outputs_scratch_tmp_peak_gib=0)


class DeviceTests(unittest.TestCase):
    def test_virtual_limit_cannot_substitute_for_gpu(self):
        result = b1.device_observation('comma mici', '19.9', 44000, None, 75000)
        self.assertIn('GPU_ACTUAL_THERMAL_UNKNOWN_OR_HIGH', result['holds'])

    def test_model_and_agnos_mismatch(self):
        result = b1.device_observation('other', '19.8.1', 44000, 41000, None)
        self.assertEqual(result['holds'], ['MODEL_MISMATCH', 'AGNOS_MISMATCH'])

    def test_idle_observation_does_not_prove_compilation(self):
        result = b1.device_observation('comma mici', '19.9', 44500, 41800, 75000)
        self.assertEqual(result['decision'], 'OBSERVED_IDLE_ONLY')


class IdentityTests(unittest.TestCase):
    def test_duplicate_manifest_keys(self):
        with self.assertRaises(ValueError):
            json.loads('{"x": 1, "x": 2}', object_pairs_hook=b1.unique_pairs)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'target').write_text('x')
            (root / 'link').symlink_to(root / 'target')
            with self.assertRaises(ValueError):
                b1.sha256(root / 'link')

    def test_bad_anchor_fails_before_source_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'manifest.json').write_text('{}')
            (root / 'source.tar').write_text('invalid')
            with self.assertRaisesRegex(ValueError, 'external anchors'):
                b1.audit(root, root, root / 'missing.log', root / 'missing.so')

    def test_plan_is_preparation_only_and_isolates_tmp(self):
        plan = qcom_b1_plan.plan()
        self.assertEqual(plan['mode'], 'PREPARATION_ONLY_NO_EXECUTE_FUNCTION')
        command = plan['conditional_commands_for_later_authorized_isolated_checkout'][-1]
        self.assertIn('TMPDIR=<isolated-data-tmp>', command)
        self.assertIn('HOME=<isolated-data-home>', command)
        self.assertIn('cache_dir=<isolated-cache>', command)
        self.assertIn('unset SKIP_TINYGRAD_COMPILE &&', command)
        self.assertEqual(len(b1.OUTPUTS), 6)


class WindowsDiagnosticsScriptTests(unittest.TestCase):
    def test_default_alias_and_native_capnpc_match_verified_windows_device(self):
        script = (Path(__file__).resolve().parents[1] / 'qcom_b1_windows_diagnostics.ps1').read_text()
        self.assertIn("[string]$HostAlias = 'comma4'", script)
        self.assertIn('/usr/local/venv/bin/capnpc', script)
        self.assertIn('-o StrictHostKeyChecking=yes', script)
        self.assertIn('PLAN ONLY:', script)


if __name__ == '__main__':
    unittest.main()
