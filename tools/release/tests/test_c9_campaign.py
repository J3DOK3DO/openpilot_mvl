from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.release import c9_b3_pilot as pilot
from tools.release import c9_b3_receipt as receipt
from tools.release import c9_r0_stage as stage


class C9CampaignTest(unittest.TestCase):
    def test_pinned_first_target_and_six_order(self):
        plan = pilot.checked_plan()
        self.assertEqual(plan['targets'][0]['stock_scons_target'], pilot.FIRST_TARGET)
        self.assertEqual([row['order'] for row in plan['targets']], list(range(1, 7)))

    def test_changed_plan_is_rejected(self):
        with patch.object(pilot, 'PLAN_SHA256', '0'*64):
            with self.assertRaisesRegex(ValueError, 'plan hash mismatch'):
                pilot.checked_plan()

    def test_active_source_and_unisolated_scratch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'active source'):
            pilot.preflight(Path('/data/openpilot'), Path('/data/mvl-builds')/pilot.SOURCE/'pilot/tmp')
        with self.assertRaisesRegex(ValueError, 'scratch must be isolated'):
            pilot.preflight(Path('/data/mvl-builds')/pilot.SOURCE/'source', Path('/data/openpilot/tmp'))

    def test_monitor_is_fail_closed(self):
        with patch('tools.release.c9_b3_pilot.subprocess.run') as run:
            run.return_value.stdout = json.dumps({'stationary': True})
            with self.assertRaisesRegex(ValueError, 'unsafe or incomplete'):
                pilot.observation(Path('/tmp/monitor'))
            run.return_value.stdout = '[]'
            with self.assertRaisesRegex(ValueError, 'must be an object'):
                pilot.observation(Path('/tmp/monitor'))

    def test_receipt_never_promotes_first_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/pilot.FIRST).write_bytes(b'fake pickle')
            (root/'compile.log').write_bytes(b'claimed success')
            report = receipt.verify({'source_commit': pilot.SOURCE, 'tinygrad_commit': pilot.TINYGRAD,
                'target': pilot.FIRST_TARGET, 'artifact': pilot.FIRST,
                'compiler_exit_code': 0, 'gpu_backend': 'QCOM'}, root/pilot.FIRST, root/'compile.log')
            self.assertEqual(report['b3_verified_artifact_count'], 0)
            self.assertFalse(report['g10_promotion'])
            self.assertTrue(report['issues'])

    def test_r0_stage_rejects_destination_outside_artifacts(self):
        with self.assertRaisesRegex(ValueError, 'C9 artifacts'):
            stage.stage(Path('/tmp'), Path('/tmp/c9-package-should-not-exist'))

    def test_r0_stage_rejects_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'already exists'):
                stage.stage(Path('/tmp'), Path(temp))


if __name__ == '__main__':
    unittest.main()
