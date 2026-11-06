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
            'tinygrad_repo_sha': probe.TINYGRAD_GITLINK,
            'tinygrad_compiler_file': 'yes',
            'data_available_kb': str(20 * 1024 * 1024),
            'tmp_available_kb': str(4 * 1024 * 1024),
            'mem_available_kb': str(4 * 1024 * 1024),
            'thermal_max_mc': '45000', 'thermal_count': '8',
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
        self.assertIn('OWNER_AND_BUILD_AUTHORIZATION', result['read_only_prerequisites'])
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ['comma', 'sh -s'])
        self.assertIn('BatchMode=yes', command)
        self.assertNotIn('/data/openpilot', command)

    def test_missing_gpu_and_thermal_hold(self):
        body = self.sample(gpu_char_device='no', thermal_max_mc='')
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, body, '')):
            result = probe.collect('comma')
        self.assertEqual(result['read_only_prerequisites'], 'OBSERVED_WITH_HOLDS')
        self.assertEqual(len(result['planning_holds']), 2)

    def test_duplicate_field_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            probe.parse_observations(self.sample() + 'arch=x86_64\n')

    def test_host_option_cannot_inject_ssh_flags(self):
        with self.assertRaisesRegex(ValueError, 'configured SSH alias'):
            probe.collect('-ProxyCommand=bad')

if __name__ == '__main__':
    unittest.main()
