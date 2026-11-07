import copy
import json
import subprocess
import sys
import unittest

from tools.release import combined_b3g10_gate as gate
from tools.release import combined_rc_readiness as rc


class CombinedRCReadinessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = gate.evaluate()

    def test_actual_pinned_gate_stays_noninstallable(self):
        report = rc.evaluate(self.base)
        self.assertEqual(report['decision'], 'RC_NOT_INSTALLABLE')
        self.assertIs(report['install_allowed'], False)
        self.assertEqual(report['b3_verified_qcom_outputs'], 0)
        self.assertEqual(report['g10_product'], 'NOT_BUILT')
        self.assertEqual(report['applicable_physical_checks_passed'], 0)
        self.assertEqual(report['formal_scoped_acceptance']['percent'], 48)
        self.assertEqual(report['formal_scoped_acceptance']['evidence_status'],
                         'HISTORICAL_NOT_REVERIFIED')
        self.assertEqual(report['installation_sequence_status'], 'PLAN_ONLY_NOT_EXECUTED')
        historical = {r['requirement']: r['status'] for r in report['checks']}
        self.assertEqual(historical['C1 non-actuating source integration'], 'HISTORICAL_NOT_REVERIFIED')
        self.assertEqual(historical['C4 host release regression'], 'HISTORICAL_NOT_REVERIFIED')
        self.assertEqual(historical['C4 254 restricted Params'], 'REQUIRED_DENY_NOT_REVERIFIED')
        self.assertEqual(historical['C4 G06 transport'], 'HISTORICAL_OFF_NOT_REVERIFIED')
        self.assertEqual(historical['C4-08 optional G06 check'], 'CONDITIONAL_NA_NOT_REVERIFIED')
        self.assertEqual({r['requirement'] for r in report['checks'] if r['status'] == 'NOT_RUN'},
                         {'C4 physical C4-01–07 and C4-09–11'})

    def test_upstream_claims_cannot_promote_release(self):
        for key, value in [('install_allowed', True), ('decision', 'PASS'),
                           ('b3_verified_artifact_count', 6), ('g10_cold_build', 'PASS'),
                           ('physical_checks_passed', 10), ('source_commit', '0'*40),
                           ('plan_sha256', '0'*64)]:
            with self.subTest(key=key):
                altered = copy.deepcopy(self.base)
                altered[key] = value
                with self.assertRaisesRegex(ValueError, 'untrusted'):
                    rc.evaluate(altered)

    def test_inventory_is_metadata_only(self):
        altered = copy.deepcopy(self.base)
        altered['artifact_inventory'] = {name: 'PRESENT_UNVERIFIED' for name in gate.NAMES}
        altered['b3_local_present_count'] = 6
        report = rc.evaluate(altered)
        self.assertEqual(report['b3_verified_qcom_outputs'], 0)
        self.assertFalse(report['install_allowed'])
        altered['artifact_inventory'][gate.NAMES[0]] = 'PASS'
        with self.assertRaisesRegex(ValueError, 'unexpected artifact'):
            rc.evaluate(altered)

    def test_rehearsal_failure_paths_are_mock_only(self):
        for failure in ('preflight_failed', 'backup_failed', 'stage_failed', 'switch_failed', 'health_failed'):
            prefix = {'preflight_failed': [], 'backup_failed': ['preflight_ok'],
                      'stage_failed': ['preflight_ok', 'backup_ok'],
                      'switch_failed': ['preflight_ok', 'backup_ok', 'stage_ok'],
                      'health_failed': ['preflight_ok', 'backup_ok', 'stage_ok', 'switch_ok']}[failure]
            result = rc.rehearse(prefix + [failure])
            self.assertEqual(result['result'], 'STOP_OWNER_RECOVERY_REQUIRED')
            self.assertFalse(result['known_good_modified'])
            self.assertFalse(result['device_write_performed'])
        self.assertEqual(rc.rehearse(['preflight_ok'])['result'], 'INCOMPLETE_NO_INSTALL')
        self.assertEqual(rc.rehearse(['preflight_ok','backup_ok','stage_ok','switch_ok','health_ok'])['result'],
                         'SIMULATED_FLOW_ONLY_NO_INSTALL_AUTHORITY')
        for bad in ([], ['stage_ok'], ['preflight_ok', 'health_failed'],
                    ['preflight_ok','backup_ok','stage_failed','health_ok']):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rc.rehearse(bad)

    def test_cli_exits_hold(self):
        run = subprocess.run([sys.executable, '-B', '-m', 'tools.release.combined_rc_readiness'],
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertFalse(json.loads(run.stdout)['install_allowed'])


if __name__ == '__main__':
    unittest.main()
