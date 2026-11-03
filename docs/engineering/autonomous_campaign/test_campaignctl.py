import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).with_name('campaignctl.py')
STATE = Path(__file__).with_name('CAMPAIGN_STATE.json')


class RecoveryTest(unittest.TestCase):
    def check_state(self, state):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            path.write_text(json.dumps(state))
            result = subprocess.run(['python3', str(SCRIPT), 'recover', '--state-file', str(path)], text=True, capture_output=True)
            return result.returncode, json.loads(result.stdout)

    def test_interrupted_operation_is_detected(self):
        state = json.loads(STATE.read_text())
        state['operation_in_progress'] = {'milestone': 'simulated-unfinished', 'started_at_utc': '2026-11-03T00:00:00Z'}
        code, result = self.check_state(state)
        self.assertEqual(code, 2)
        self.assertEqual(result['pending_operation']['milestone'], 'simulated-unfinished')
        self.assertIn('operation was interrupted or remains in progress', result['problems'])

    def test_run_lease_prevents_overlap_and_unowned_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, CAMPAIGN_LEASE_DIR=str(Path(directory) / 'lease'),
                       CAMPAIGN_LOCK_FILE=str(Path(directory) / 'command.lock'))
            first = subprocess.run(['python3', str(SCRIPT), 'claim-run'], env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0)
            token = first.stdout.strip()
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'claim-run'], env=env, capture_output=True).returncode, 3)
            self.assertNotEqual(subprocess.run(['python3', str(SCRIPT), 'locked-run', '--', 'true'], env=env, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'locked-run', '--token', token, '--', 'true'], env=env, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'finish-run', 'wrong'], env=env, capture_output=True).returncode, 3)
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'finish-run', token], env=env, capture_output=True).returncode, 0)

    def test_interrupted_lease_can_be_reclaimed_only_after_expiry(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, CAMPAIGN_LEASE_DIR=str(Path(directory) / 'lease'),
                       CAMPAIGN_LOCK_FILE=str(Path(directory) / 'command.lock'),
                       CAMPAIGN_LEASE_TTL_SECONDS='0')
            first = subprocess.run(['python3', str(SCRIPT), 'claim-run'], env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0)
            old_token = first.stdout.strip()
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'claim-run'], env=env, capture_output=True).returncode, 3)
            time.sleep(0.01)
            second = subprocess.run(['python3', str(SCRIPT), 'claim-run', '--reclaim-stale'], env=env, text=True, capture_output=True)
            self.assertEqual(second.returncode, 0)
            new_token = second.stdout.strip()
            self.assertNotEqual(old_token, new_token)
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'locked-run', '--token', old_token, '--', 'true'], env=env, capture_output=True).returncode, 3)
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'locked-run', '--token', new_token, '--', 'true'], env=env, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(['python3', str(SCRIPT), 'finish-run', new_token], env=env, capture_output=True).returncode, 0)

    def test_checkpoint_drift_is_detected(self):
        state = json.loads(STATE.read_text())
        state['active_engineering']['head'] = '0' * 40
        code, result = self.check_state(state)
        self.assertEqual(code, 2)
        self.assertIn('HEAD differs from recorded checkpoint', result['problems'])


if __name__ == '__main__':
    unittest.main()
