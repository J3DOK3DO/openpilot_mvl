from __future__ import annotations

import json
from pathlib import Path
import hashlib
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

    def test_execute_rejects_missing_hard_quota_and_io_cap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            monitor = root/'monitor'
            monitor.write_text('#!/bin/sh\nexit 0\n')
            monitor.chmod(0o700)
            gate = {'source_commit': pilot.SOURCE, 'target': pilot.FIRST_TARGET,
                    'max_seconds': 300, 'monitor_sha256': hashlib.sha256(monitor.read_bytes()).hexdigest(),
                    'peak_scratch_bytes': 1}
            for key in ('coordinator_approved', 'independent_physical_monitor_qualified',
                        'sustained_external_power_qualified', 'thermal_gpu_monitor_qualified',
                        'cgroup_abort_rehearsed', 'stock_safety_qualified', 'rollback_ready'):
                gate[key] = True
            gate_file = root/'gate.json'
            gate_file.write_text(json.dumps(gate))
            with patch.object(pilot, 'preflight'):
                with self.assertRaisesRegex(ValueError, 'physical gate incomplete'):
                    pilot.execute(root/'source', root/'scratch', gate_file, monitor, root/'log')
                gate['aggregate_hard_quota_qualified'] = True
                gate_file.write_text(json.dumps(gate))
                with self.assertRaisesRegex(ValueError, 'hard quota or bounded IO'):
                    pilot.execute(root/'source', root/'scratch', gate_file, monitor, root/'log')
                gate['peak_scratch_bytes'] = True
                gate_file.write_text(json.dumps(gate))
                with self.assertRaisesRegex(ValueError, 'measured peak scratch'):
                    pilot.execute(root/'source', root/'scratch', gate_file, monitor, root/'log')

    def test_r0_stage_rejects_destination_outside_artifacts(self):
        with self.assertRaisesRegex(ValueError, 'C9 artifacts'):
            stage.stage(Path('/tmp'), Path('/tmp/c9-package-should-not-exist'))

    def test_r0_stage_rejects_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'already exists'):
                stage.stage(Path('/tmp'), Path(temp))


if __name__ == '__main__':
    unittest.main()
