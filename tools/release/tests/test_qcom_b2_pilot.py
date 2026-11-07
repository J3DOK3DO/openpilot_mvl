import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.release import qcom_b2_pilot as b2


NOW = 1000.0


def good_evidence():
    return {
        'source_commit': b2.SOURCE, 'source_verified': True,
        'installed_commit': b2.INSTALLED, 'installed_untouched': True,
        'agnos': '19.9', 'model': 'comma mici',
        'handoff_sha_verified': True, 'submodules_verified': True, 'onnx_verified': True,
        'no_control_or_panda_process': True, 'operator_armed': True,
        'proof_authenticated': True, 'telemetry_subscription_ok': True,
        'monitor_subscription_ok': True,
        'samples': [
            {'monotonic': t, 'panda_ignition': False, 'car_parked': True,
             'engaged': False, 'panda_fresh': True, 'car_state_fresh': True}
            for t in range(960, 1000)],
        'thermal_sensors': {'cpu_actual': 44000, 'gpu_actual': 41000},
        'mem_available_bytes': 3 * b2.GIB, 'data_free_bytes': 5 * b2.GIB,
        'hard_storage_quota_bytes': b2.PILOT_LIMIT, 'quota_enforced_independently': True,
        'memory_limit_bytes': 512 * 1024 ** 2, 'memory_limit_enforced': True,
        'fresh_monitor_max_age_seconds': 1, 'monitor_abort_on_stale': True,
        'monitor_abort_on_ignition': True, 'monitor_abort_on_engagement': True,
        'monitor_abort_on_thermal': True, 'monitor_abort_on_low_disk': True,
        'monitor_abort_on_memory': True, 'monitor_abort_on_timeout': True,
        'monitor_kill_process_group': True, 'monitor_watchdog_independent': True,
        'cpu_affinity_0_7_verified': True,
        'pilot_path': str(b2.pilot_path('0123456789abcdef')),
    }


class PolicyTests(unittest.TestCase):
    def test_complete_fixture_only_eligible_not_execution(self):
        self.assertEqual(b2.evaluate(good_evidence(), NOW), [])

    def test_abort_and_failure_cases(self):
        cases = [
            ('source_commit', 'bad', 'SOURCE_IDENTITY_UNVERIFIED'),
            ('handoff_sha_verified', False, 'SOURCE_CONTENT_UNVERIFIED'),
            ('no_control_or_panda_process', False, 'CONTROL_PROCESS_PRESENT_OR_UNKNOWN'),
            ('telemetry_subscription_ok', False, 'LIVE_TELEMETRY_UNAVAILABLE'),
            ('monitor_subscription_ok', False, 'LIVE_TELEMETRY_UNAVAILABLE'),
            ('data_free_bytes', b2.RESERVE + b2.PILOT_LIMIT - 1, 'DISK_RESERVE_OR_PILOT_BUDGET_MISSING'),
            ('mem_available_bytes', b2.GIB, 'RAM_HEADROOM_UNVERIFIED'),
            ('hard_storage_quota_bytes', None, 'HARD_STORAGE_QUOTA_UNVERIFIED'),
            ('monitor_abort_on_stale', False, 'FAIL_SAFE_MONITOR_UNVERIFIED'),
            ('pilot_path', '/data/openpilot/pilot-0123456789abcdef', 'ISOLATION_PATH_UNVERIFIED'),
            ('pilot_path', '/data/mvl-builds/' + b2.SOURCE + '/pilot-../../openpilot', 'ISOLATION_PATH_UNVERIFIED'),
        ]
        for field, value, block in cases:
            with self.subTest(field=field, value=value):
                e = good_evidence(); e[field] = value
                self.assertIn(block, b2.evaluate(e, NOW))

    def test_idle_single_sample_or_stale_monitor_rejected(self):
        for samples in ([good_evidence()['samples'][0]], good_evidence()['samples'][:30]):
            e = good_evidence(); e['samples'] = samples
            self.assertIn('CONTINUOUS_PARKED_OFF_PROOF_MISSING', b2.evaluate(e, NOW))
        e = good_evidence(); e['samples'][-1]['monotonic'] = 990
        self.assertIn('CONTINUOUS_PARKED_OFF_PROOF_MISSING', b2.evaluate(e, NOW))
        e = good_evidence(); e['samples'].pop(20)
        self.assertIn('CONTINUOUS_PARKED_OFF_PROOF_MISSING', b2.evaluate(e, NOW))

    def test_ignition_engagement_and_missing_car_state_abort(self):
        for field, value in [('panda_ignition', True), ('engaged', True),
                             ('car_parked', False), ('car_state_fresh', False)]:
            with self.subTest(field=field):
                e = good_evidence(); e['samples'][-1][field] = value
                self.assertIn('CONTINUOUS_PARKED_OFF_PROOF_MISSING', b2.evaluate(e, NOW))

    def test_virtual_thermal_or_unknown_sensor_rejected(self):
        for sensors in ({'lmh-dcvs': 75000, 'gpu_actual': 41000},
                        {'cpu_actual': 44000}, {'cpu_actual': 44000, 'gpu_actual': 70000}):
            e = good_evidence(); e['thermal_sensors'] = sensors
            self.assertIn('ACTUAL_CPU_GPU_THERMAL_UNVERIFIED', b2.evaluate(e, NOW))

    def test_symlink_component_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'alias').symlink_to(root / 'real')
            self.assertFalse(b2.no_symlink_components(root / 'alias' / 'source'))
            self.assertFalse(b2.no_symlink_components(root / '..' / 'bad'))

    def test_run_id_rejects_shell_and_powershell_metacharacters(self):
        for run_id in ('../openpilot', '0123456789abcdef;touch /tmp/x',
                       '$(id)', '`id`', "a'b", 'A' * 16, 'a' * 15):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                b2.pilot_path(run_id)
        self.assertEqual(b2.pilot_path('0123456789abcdef').parent.name, b2.SOURCE)

    def test_plan_is_argv_without_shell(self):
        p = b2.plan('0123456789abcdef')
        self.assertEqual(p['conditional_scons_argv'][-1], b2.TARGET)
        self.assertEqual(p['qcom_flags'], b2.FLAGS)
        self.assertTrue(p['cwd'].endswith('/source'))
        self.assertIn('SKIP_TINYGRAD_COMPILE', p['unset_environment'])
        self.assertNotIn('SKIP_TINYGRAD_COMPILE', p['environment'])

    def test_cli_execute_denies_without_creating_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / 'untouched'
            code = Path(b2.__file__)
            p = subprocess.run([sys.executable, str(code), '--execute', '--run-id',
                                '0123456789abcdef'], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(json.loads(p.stdout)['decision'], 'NO_GO_EXECUTION_DISABLED')
            self.assertFalse(marker.exists())

    def test_read_only_inspect_failure(self):
        with patch.object(b2, 'read_git_head', return_value=None), \
             patch.object(b2.os, 'statvfs', side_effect=OSError), \
             patch.object(b2.Path, 'read_text', side_effect=OSError):
            result = b2.inspect('0123456789abcdef')
        self.assertEqual(result['decision'], 'NO_GO_LIVE_TELEMETRY_AND_HARD_QUOTA_UNVERIFIED')
        self.assertIsNone(result['data_available_bytes'])
        self.assertIsNone(result['mem_available_bytes'])


if __name__ == '__main__':
    unittest.main()
