import json
from pathlib import Path
import subprocess
import tempfile
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

    def test_checkpoint_drift_is_detected(self):
        state = json.loads(STATE.read_text())
        state['active_engineering']['head'] = '0' * 40
        code, result = self.check_state(state)
        self.assertEqual(code, 2)
        self.assertIn('HEAD differs from recorded checkpoint', result['problems'])


if __name__ == '__main__':
    unittest.main()
