"""Fail-closed offline pilot test; does not contact a Comma device."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.release import c9_b3_pilot as pilot


class C10InterlockTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.source = self.root / 'source'
        self.scratch = self.root / 'scratch'
        self.source.mkdir()
        self.scratch.mkdir()

    def test_valid_new_scratch_log(self):
        pilot.check_execution_log_path(self.source, self.scratch, self.scratch / 'first-warp.log')

    def test_invalid_log_paths_rejected(self):
        existing = self.scratch / 'existing.log'
        existing.write_text('retain')
        other = self.root / 'other'
        other.write_text('retain')
        link = self.scratch / 'symlink.log'
        link.symlink_to(other)
        paths = [
            self.source / 'log', Path('/data/openpilot/compilation.log'),
            self.root / 'outside.log', Path('relative.log'),
            self.scratch / 'nested' / 'log', self.scratch / '..' / 'escape.log',
            existing, link,
        ]
        for p in paths:
            with self.subTest(path=str(p)), self.assertRaisesRegex(ValueError, 'execution log'):
                pilot.check_execution_log_path(self.source, self.scratch, p)
        self.assertEqual(existing.read_text(), 'retain')

    def test_reject_source_and_active_scratch(self):
        for s in (self.source / 'nested', Path('/data/openpilot/isolated')):
            with self.subTest(scratch=str(s)), self.assertRaises(ValueError):
                pilot.check_execution_log_path(self.source, s, s / 'log')

    def test_bad_log_rejected_before_gate_or_scratch_write(self):
        with patch.object(pilot, 'preflight', return_value={}):
            with self.assertRaisesRegex(ValueError, 'execution log'):
                pilot.execute(self.source, self.scratch, self.root / 'missing-gate.json',
                              self.source / 'monitor', self.source / 'bad.log')
        self.assertEqual(sorted(self.scratch.iterdir()), [])

    def test_execution_error_is_unknown_write_and_hold(self):
        argv = ['pilot', '--source', str(self.source), '--scratch', str(self.scratch),
                '--execute', '--gate', 'g', '--monitor', 'm', '--log', 'l']
        out = io.StringIO()
        with patch('sys.argv', argv), patch('sys.stdout', out), patch.object(
                pilot, 'execute', side_effect=TimeoutError('simulated abort')):
            self.assertEqual(pilot.main(), 2)
        result = json.loads(out.getvalue())
        self.assertEqual(result['decision'], 'HOLD')
        self.assertIsNone(result['device_write_performed'])
        self.assertEqual(result['write_state'], 'UNKNOWN_REQUIRES_DEVICE_REVIEW')
        self.assertFalse(result['install_allowed'])

    def test_readonly_error_is_no_write(self):
        out = io.StringIO()
        with patch('sys.argv', ['pilot', '--source', 's', '--scratch', 'x']), patch(
                'sys.stdout', out), patch.object(pilot, 'preflight', side_effect=ValueError('bad')):
            self.assertEqual(pilot.main(), 2)
        result = json.loads(out.getvalue())
        self.assertIs(result['device_write_performed'], False)
        self.assertEqual(result['write_state'], 'NOT_ATTEMPTED')

    @staticmethod
    def monitor(**overrides):
        obj = dict(authenticated=True, stationary=True, physically_disconnected=True,
                   offroad=True, external_power_stable=True, thermal_within_limit=True,
                   gpu_error_free=True, abort_ready=True, stock_manager_healthy=True,
                   panda_ignition_can=False, panda_ignition_line=False, engaged=False,
                   speed_mps=0, cpu_temp_c=38, gpu_temp_c=41,
                   gpu_errors=0, memory_oom_events=0, external_power_duration_seconds=360,
                   observed_at_utc=datetime.now(timezone.utc).isoformat())
        obj.update(overrides)
        return obj

    @staticmethod
    def check_observation(obj):
        with patch.object(pilot.subprocess, 'run') as command:
            command.return_value.stdout = json.dumps(obj)
            return pilot.observation(Path('/tmp/synthetic-monitor'))

    def test_synthetic_monitor_schema_only(self):
        self.assertTrue(self.check_observation(self.monitor())['authenticated'])

    def test_monitor_disqualifiers(self):
        bad = [
            {'authenticated': False}, {'stationary': False},
            {'physically_disconnected': False}, {'offroad': False},
            {'external_power_stable': False}, {'thermal_within_limit': False},
            {'gpu_error_free': False}, {'abort_ready': False},
            {'stock_manager_healthy': False}, {'panda_ignition_can': True},
            {'panda_ignition_line': True}, {'engaged': True},
            {'speed_mps': True}, {'speed_mps': 0.01},
            {'cpu_temp_c': 70}, {'gpu_temp_c': -1},
            {'gpu_errors': 1}, {'memory_oom_events': 1},
            {'external_power_duration_seconds': 299},
            {'observed_at_utc': (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()},
            {'observed_at_utc': (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()},
        ]
        for change in bad:
            with self.subTest(change=change), self.assertRaises((ValueError, KeyError, TypeError)):
                self.check_observation(self.monitor(**change))

    def test_windows_log_path_guard(self):
        text = (Path(__file__).parents[1] / 'c9_b3_windows_pilot.ps1').read_text()
        self.assertIn('Log must be a direct child of isolated scratch', text)
        self.assertIn('PYTHONDONTWRITEBYTECODE=1', text)
        self.assertIn("'python3', '-B', '-m'", text)


if __name__ == '__main__':
    unittest.main()
