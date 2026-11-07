import unittest
from tools.release import campaign2_hardware_gate as gate


class HardwareGateTest(unittest.TestCase):
    def observation(self):
        return {'schema_version': 1, 'scope': 'read-only device observations',
                'fields': {'model': 'comma mici', 'arch': 'aarch64', 'agnos': '19.9',
                           'installed_sha': gate.INSTALLED, 'installed_branch': 'sp-honda-dev-202608',
                           'data_mount': '40 17 8:12 / /data rw - ext4 /dev/sda12 rw,data=ordered',
                           'data_ext4_features': 'has_journal extent metadata_csum',
                           'data_free_kib': '9284160', 'cgroup_type': 'cgroup2fs',
                           'cgroup_controllers': 'memory',
                           'thermals': ['cpu0-usr|42000|/sys/class/thermal/thermal_zone1/temp',
                                        'gpu0-usr|39000|/sys/class/thermal/thermal_zone11/temp']}}

    def test_actual_readonly_facts_cannot_promote_quota_or_pilot(self):
        report = gate.assess(self.observation())
        rows = {x['requirement']: x['status'] for x in report['rows']}
        self.assertEqual(report['decision'], 'B2_HARDWARE_NOT_QUALIFIED')
        self.assertEqual(rows['ext4_project_quota_capability'], 'FAIL')
        self.assertEqual(rows['aggregate_hard_storage_limit'], 'UNKNOWN')
        self.assertEqual(rows['gpu_memory_containment'], 'UNKNOWN')
        self.assertEqual(rows['continuous_parked_disengaged_state'], 'UNKNOWN')
        self.assertEqual(rows['device_and_known_good_identity'], 'PASS')

    def test_false_claims_and_identity_mismatch_fail_closed(self):
        obs = self.observation()
        obs['fields']['installed_sha'] = '0'*40
        obs['fields']['data_ext4_features'] += ' project quota'
        obs['fields']['data_mount'] += ',prjquota'
        rows = {x['requirement']: x['status'] for x in gate.assess(obs)['rows']}
        self.assertEqual(rows['device_and_known_good_identity'], 'FAIL')
        self.assertEqual(rows['aggregate_hard_storage_limit'], 'UNKNOWN')
        self.assertEqual(rows['independent_abort_and_cleanup'], 'UNKNOWN')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            gate.unique_pairs([('scope','read-only'),('scope','read-only')])


if __name__ == '__main__': unittest.main()
