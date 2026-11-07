import copy
from pathlib import Path
import tempfile
import unittest

from tools.release import campaign3_offline as c


def storage():
    root = '/tmp/pilot-0123456789abcdef'
    return {'run_root': root, 'write_paths': {x: root + '/' + x for x in c.WRITE_AREAS},
            'free_bytes': 8*c.GIB, 'hard_limit_bytes': 3*c.GIB,
            'measured_source_bytes': c.GIB, 'method': 'ext4_project_quota',
            'observed_filesystem': 'ext4',
            'capability': {x: True for x in ('active_feature', 'active_mount', 'isolated_run',
                'all_writes_confined', 'hard_enospc_tested', 'no_external_writes',
                'cleanup_provenance_verified', 'observed_data_ext4_project_feature')}}


def frames():
    return [{'at': float(i),
             'pandaStates': {'timestamp': float(i), 'alive': True, 'valid': True,
                             'value': {'ignitionCan': False, 'ignitionLine': False}},
             'carState': {'timestamp': float(i), 'alive': True, 'valid': True, 'value': {'vEgo': 0.0}},
             'controlsState': {'timestamp': float(i), 'alive': True, 'valid': True,
                               'value': {'enabled': False}}} for i in range(31)]


class Campaign3OfflineTest(unittest.TestCase):
    def test_storage_candidate_never_proves_enforcement(self):
        result = c.storage_assessment(storage())
        self.assertEqual(result['decision'], 'OFFLINE_CANDIDATE_ONLY')
        self.assertFalse(result['aggregate_hard_limit_enforced'])
        self.assertTrue(result['preferred_four_gib_reserve'])

    def test_storage_fail_closed(self):
        for mutate in (lambda s: s['capability'].update(observed_data_ext4_project_feature=False),
                       lambda s: s.update(hard_limit_bytes=7*c.GIB),
                       lambda s: s.update(method='xfs_project_quota'),
                       lambda s: s['capability'].update(no_external_writes=False)):
            spec = storage(); mutate(spec)
            self.assertEqual(c.storage_assessment(spec)['decision'], 'NO_GO')
        for path in ('/tmp/elsewhere', '/tmp/pilot-0123456789abcdef/../escape',
                     '/tmp/pilot-0123456789abcdef/cache/other'):
            spec = storage(); spec['write_paths']['cache'] = path
            with self.assertRaises(ValueError): c.storage_assessment(spec)
        spec = storage(); spec['write_paths'].pop('diagnostics')
        with self.assertRaises(ValueError): c.storage_assessment(spec)
        spec = storage(); spec['hard_limit_bytes'] = True
        with self.assertRaises(ValueError): c.storage_assessment(spec)
        spec = storage(); spec['run_root'] = '/tmp'
        with self.assertRaises(ValueError): c.storage_assessment(spec)

    def test_containment_requires_independent_cgroup_owner(self):
        keys = ('independent_supervisor', 'supervisor_survives_guardian_sigkill',
                'worker_cgroup_owned', 'all_descendants_confined', 'cgroup_kill_available',
                'guardian_liveness_observed', 'supervisor_liveness_observed',
                'bounded_kill_verified', 'empty_cgroup_verified', 'cleanup_owned_and_verified')
        spec = {'mechanism': 'independent_cgroup_v2', **{key: True for key in keys}}
        self.assertEqual(c.containment_assessment(spec)['decision'], 'OFFLINE_DESIGN_COMPLETE_DEVICE_HOLD')
        for key in keys:
            bad = dict(spec); bad[key] = False
            self.assertEqual(c.containment_assessment(bad)['decision'], 'NO_GO', key)
        for mechanism in ('process_group', 'prctl_parent_death_signal', 'systemd_scope_unverified'):
            bad = dict(spec); bad['mechanism'] = mechanism
            self.assertEqual(c.containment_assessment(bad)['decision'], 'NO_GO')
        cases = {
            'worker_group_persists_after_guardian_kill': {'supervisor_survives_guardian_sigkill': False,
                                                          'bounded_kill_verified': False},
            'orphaned_grandchild_escapes_group': {'all_descendants_confined': False,
                                                 'empty_cgroup_verified': False},
            'no_independent_supervisor': {'independent_supervisor': False,
                                          'supervisor_liveness_observed': False},
        }
        for label, changes in cases.items():
            bad = dict(spec); bad.update(changes)
            self.assertEqual(c.containment_assessment(bad)['decision'], 'NO_GO', label)

    def test_replay_positive_and_negative(self):
        self.assertEqual(c.replay_state(frames())['decision'], 'SYNTHETIC_POLICY_PASS_DEVICE_HOLD')
        for service in c.SERVICES:
            for field, value in (('alive', False), ('valid', False), ('timestamp', 7.0)):
                stream = frames(); stream[15][service][field] = value
                self.assertEqual(c.replay_state(stream)['decision'], 'NO_GO', (service, field))
            stream = frames(); del stream[15][service]
            self.assertEqual(c.replay_state(stream)['decision'], 'NO_GO')
        changes = (('pandaStates','ignitionCan',True), ('pandaStates','ignitionLine',None),
                   ('carState','vEgo',0.02), ('carState','vEgo',-0.01),
                   ('controlsState','enabled',True))
        for service, key, value in changes:
            stream = frames(); stream[15][service]['value'][key] = value
            self.assertEqual(c.replay_state(stream)['decision'], 'NO_GO', (service, key))

    def test_replay_gap_skew_and_duration(self):
        stream = frames(); stream[15]['at'] = 16.5
        self.assertEqual(c.replay_state(stream)['decision'], 'NO_GO')
        stream = frames(); stream[15]['carState']['timestamp'] = 14.7
        self.assertIn('TIMESTAMP_SKEW', c.replay_state(stream)['reasons'])
        self.assertEqual(c.replay_state(frames()[:-1])['decision'], 'NO_GO')
        stream = frames()
        for index, frame in enumerate(stream):
            frame['at'] = index * 0.99
            for service in c.SERVICES:
                frame[service]['timestamp'] = frame['at']
        self.assertIn('DURATION_SHORT', c.replay_state(stream)['reasons'])
        stream = frames(); stream[15]['carState']['value']['vEgo'] = float('nan')
        self.assertEqual(c.replay_state(stream)['decision'], 'NO_GO')
        stream = frames(); stream[15]['controlsState']['value']['enabled'] = 0
        self.assertEqual(c.replay_state(stream)['decision'], 'NO_GO')

    def test_replay_requires_each_service_timestamp_to_advance(self):
        for change, services in (('repeat', ('carState',)),
                                 ('repeat', c.SERVICES),
                                 ('decrease', ('carState',)),
                                 ('decrease', c.SERVICES)):
            with self.subTest(change=change, services=services):
                stream = frames()
                stream.append(copy.deepcopy(stream[-1]))
                for index, frame in enumerate(stream):
                    at = 0.0 if index == 0 else index - 0.5
                    frame['at'] = at
                    for service in c.SERVICES:
                        frame[service]['timestamp'] = at
                if change == 'decrease':
                    for service in c.SERVICES:
                        stream[0][service]['timestamp'] = -0.2
                    for service in c.SERVICES:
                        stream[1][service]['timestamp'] = -0.1
                    for service in services:
                        stream[1][service]['timestamp'] = -0.3
                else:
                    for service in c.SERVICES:
                        stream[1][service]['timestamp'] = 0.2
                    for service in services:
                        stream[1][service]['timestamp'] = 0.0
                result = c.replay_state(stream)
                self.assertEqual(result['decision'], 'NO_GO')
                self.assertEqual(result['reasons'], ['SERVICE_TIMESTAMP_NONMONOTONIC'])


if __name__ == '__main__': unittest.main()
