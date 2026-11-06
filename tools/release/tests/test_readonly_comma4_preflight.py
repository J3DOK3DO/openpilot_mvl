import subprocess
import unittest
from unittest.mock import patch
from tools.release import readonly_comma4_preflight as probe

class ReadOnlyComma4PreflightTest(unittest.TestCase):
    def sample(self, **changes):
        values = {key: '' for key in probe.FIELDS}
        values.update({
            'model': 'comma four', 'arch': 'aarch64', 'agnos_version': '19.8.1',
            'agnos_marker': 'yes', 'gpu_char_device': 'yes',
            'python3_path': '/usr/bin/python3', 'clang_path': '/usr/bin/clang',
            'clangxx_path': '/usr/bin/clang++', 'capnpc_path': '/usr/bin/capnpc',
            'scons_path': '/usr/local/venv/bin/scons',
            'scons_candidate_path': '/usr/local/venv/bin/scons',
            'capnpc_candidate_path': '/usr/local/venv/bin/capnpc',
            'scons_module': 'yes',
            'tinygrad_repo_sha': probe.TINYGRAD_GITLINK,
            'tinygrad_compiler_file': 'yes',
            'data_available_kb': str(20 * 1024 * 1024),
            'tmp_available_kb': str(4 * 1024 * 1024),
            'mem_available_kb': str(4 * 1024 * 1024),
            'cpu_gpu_thermal_max_mc': '45000', 'cpu_gpu_thermal_count': '8',
            'limit_thermal_max_mc': '75000', 'limit_thermal_count': '2',
            'installed_branch': 'known-good-example', 'installed_sha': 'a' * 40,
        })
        values.update(changes)
        return ''.join(f'{key}={value}\n' for key, value in sorted(values.items()))

    def test_unreachable_keeps_device_qualification_untested(self):
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 255, '', 'No route to host')):
            result = probe.collect('comma')
        self.assertEqual(result['status'], 'UNREACHABLE')
        self.assertEqual(result['failure_class'], 'NO_ROUTE_TO_HOST')
        self.assertEqual(result['qualification_decision'], 'NOT_TESTED')
        self.assertNotIn('observations', result)

    def test_observation_never_claims_build_or_known_good(self):
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, self.sample(), '')) as run:
            result = probe.collect('comma')
        self.assertEqual(result['status'], 'OBSERVED_READ_ONLY')
        self.assertFalse(result['known_good_confirmed_by_owner'])
        self.assertEqual(result['qualification_decision'], 'NOT_TESTED')
        self.assertEqual(result['read_only_prerequisites'], 'OBSERVED_COMPATIBILITY_PENDING')
        self.assertEqual(result['agnos_compatibility'], 'OBSERVED_COMPATIBILITY_PENDING')
        self.assertEqual(result['storage_plan']['status'], 'REQUIRED_CAPACITY_UNKNOWN')
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ['comma', 'sh -s'])
        self.assertIn('BatchMode=yes', command)
        self.assertNotIn('/data/openpilot', command)

    def test_missing_gpu_and_thermal_hold(self):
        body = self.sample(gpu_char_device='no', cpu_gpu_thermal_max_mc='')
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, body, '')):
            result = probe.collect('comma')
        self.assertEqual(result['read_only_prerequisites'], 'OBSERVED_WITH_HOLDS')
        self.assertEqual(len(result['planning_holds']), 2)

    def test_collected_build_prerequisites_all_hold_when_wrong(self):
        changes = dict(model='other hardware', tinygrad_repo_sha='0' * 40, tinygrad_compiler_file='no', scons_path='', scons_candidate_path='', scons_module='no', data_available_kb='1')
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, self.sample(**changes), '')):
            result = probe.collect('comma')
        self.assertEqual(result['read_only_prerequisites'], 'OBSERVED_WITH_HOLDS')
        self.assertEqual(len(result['planning_holds']), 4)

    def test_agnos_199_mici_and_limit_zone_do_not_make_false_hold(self):
        body = self.sample(model='comma mici', agnos_version='19.9', tmp_available_kb='153600',
                           cpu_gpu_thermal_max_mc='49400', limit_thermal_max_mc='75000',
                           capnpc_path='', scons_path='')
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, body, '')):
            result = probe.collect('comma')
        self.assertEqual(result['planning_holds'], [])
        self.assertEqual(result['build_target_match'], 'BUILD_TARGET_MISMATCH')
        self.assertEqual(result['storage_plan']['status'], 'REQUIRED_CAPACITY_UNKNOWN')
        self.assertEqual(result['qualification_decision'], 'NOT_TESTED')

    def test_missing_actual_sensor_and_unresolved_tools_hold(self):
        body = self.sample(cpu_gpu_thermal_count='0', cpu_gpu_thermal_max_mc='',
                           scons_path='', scons_candidate_path='', scons_module='no',
                           capnpc_path='', capnpc_candidate_path='')
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, body, '')):
            result = probe.collect('comma')
        self.assertEqual(len(result['planning_holds']), 3)
        self.assertEqual(result['read_only_prerequisites'], 'OBSERVED_WITH_HOLDS')

    def test_low_disk_and_unknown_disk_never_pass(self):
        for available in ('1', ''):
            with self.subTest(available=available):
                body = self.sample(data_available_kb=available)
                with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, body, '')):
                    result = probe.collect('comma')
                self.assertEqual(result['read_only_prerequisites'], 'OBSERVED_WITH_HOLDS')
                self.assertEqual(result['storage_plan']['status'], 'REQUIRED_CAPACITY_UNKNOWN')

    def test_duplicate_field_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            probe.parse_observations(self.sample() + 'arch=x86_64\n')

    def test_host_option_cannot_inject_ssh_flags(self):
        with self.assertRaisesRegex(ValueError, 'configured SSH alias'):
            probe.collect('-ProxyCommand=bad')

if __name__ == '__main__':
    unittest.main()
