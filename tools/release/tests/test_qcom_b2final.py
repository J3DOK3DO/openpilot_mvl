import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tools.release import qcom_b2final as b


class B2FinalTest(unittest.TestCase):
    def sample(self, t, **changes):
        values = dict(monotonic=t, received_at=t, panda_ignition_can=False,
                      panda_ignition_line=False, car_parked=True, speed_mps=0.0,
                      engaged=False, panda_fresh=True, car_fresh=True,
                      controls_fresh=True, authenticated=True)
        values.update(changes)
        return b.Sample(**values)

    def test_live_proof_requires_full_fresh_authenticated_stream(self):
        samples = [self.sample(float(i)) for i in range(31)]
        self.assertEqual(b.preflight(samples, 30.5), [])
        self.assertIn('CONTINUOUS_30_SECOND_PROOF_MISSING', b.preflight(samples[:10], 10))
        self.assertIn('TELEMETRY_CADENCE_OR_DURATION_INVALID', b.preflight(samples[:15] + [self.sample(17)] + samples[16:], 30))
        self.assertIn('TELEMETRY_UNAUTHENTICATED', b.preflight(samples[:10] + [self.sample(10, authenticated='yes')] + samples[11:], 30.5))
        self.assertIn('REQUIRED_TELEMETRY_MISSING', b.preflight(samples[:10] + [self.sample(10, car_fresh=False)] + samples[11:], 30.5))
        self.assertIn('VEHICLE_NOT_PROVEN_PARKED_OFF', b.preflight(samples[:10] + [self.sample(10, panda_ignition_can=True)] + samples[11:], 30.5))
        self.assertIn('VEHICLE_NOT_PROVEN_PARKED_OFF', b.preflight(samples[:10] + [self.sample(10, speed_mps=0.1)] + samples[11:], 30.5))
        self.assertIn('TELEMETRY_STALE', b.preflight(samples, 40))

    def test_resource_abort_fail_closed(self):
        safe = dict(cpu_c=44, gpu_c=42, mem_available=2*b.GIB, data_free=4*b.GIB,
                    memory_oom_events=0, gpu_errors=0, heartbeat_age=0.2, quota_breached=False,
                    foreign_process=False, operator_abort=False, connection_alive=True)
        self.assertEqual(b.resource_reasons(**safe), [])
        for key, value, label in [('cpu_c', 70, 'ACTUAL_THERMAL_UNSAFE_OR_MISSING'),
                                  ('gpu_c', None, 'ACTUAL_THERMAL_UNSAFE_OR_MISSING'),
                                  ('mem_available', 1, 'MEMORY_HEADROOM_LOW_OR_MISSING'),
                                  ('data_free', 1, 'DISK_RESERVE_LOW_OR_MISSING'),
                                  ('memory_oom_events', 1, 'OOM_EVENT_OR_COUNTER_MISSING'),
                                  ('gpu_errors', 1, 'GPU_ERROR_OR_COUNTER_MISSING'),
                                  ('heartbeat_age', 2, 'WATCHDOG_HEARTBEAT_LOST'),
                                  ('quota_breached', None, 'QUOTA_BREACH_OR_UNKNOWN'),
                                  ('foreign_process', True, 'UNEXPECTED_PROCESS_OR_UNKNOWN'),
                                  ('operator_abort', True, 'OPERATOR_ABORT_OR_UNKNOWN'),
                                  ('connection_alive', False, 'CONTROLLER_CONNECTION_LOST_OR_UNKNOWN')]:
            changed = dict(safe, **{key: value})
            self.assertIn(label, b.resource_reasons(**changed))

    def test_quota_does_not_claim_device_enforcement(self):
        r = b.quota_assessment(filesystem='ext4', project_quota_active=True,
            tested_hard_limit=True, all_writes_confined=True,
            requested_bytes=512*1024**2, measured_source_bytes=1009*1024**2)
        self.assertFalse(r['source_fits_before_scratch'])
        self.assertEqual(r['decision'], 'NOT_VERIFIED_OR_INSUFFICIENT')
        self.assertFalse(r['device_qualified'])

    def test_paths_and_device_execution_locked(self):
        with self.assertRaises(ValueError): b.pilot_path('../unsafe')
        with self.assertRaises(ValueError): b.pilot_path('A'*16)
        p = subprocess.run([sys.executable, 'tools/release/qcom_b2final.py', '--run-id', 'a'*16, '--execute'],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)['decision'], 'NO_GO_EXECUTION_DISABLED')

    def make_fixture(self, root, run_id='a'*16, nonce='owner-token'):
        d = b.pilot_path(run_id, root)
        d.mkdir(parents=True)
        st = d.stat()
        (d/'owner.json').write_text(json.dumps({'run_id':run_id,'source':b.SOURCE,
            'nonce':nonce,'device':st.st_dev,'inode':st.st_ino}))
        (d/'cache').mkdir()
        (d/'cache'/'part').write_bytes(b'partial')
        return d

    def test_cleanup_verified_fixture_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = self.make_fixture(root)
            result = b.cleanup_host_fixture(d, root, 'a'*16, 'owner-token', worker_stopped=True)
            self.assertEqual(result['status'], 'REMOVED_VERIFIED_HOST_FIXTURE')
            self.assertEqual(b.cleanup_host_fixture(d, root, 'a'*16, 'owner-token', worker_stopped=True)['status'], 'ALREADY_ABSENT')

    def test_cleanup_rejects_symlink_owner_and_worker_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = self.make_fixture(root)
            (d/'cache'/'escape').symlink_to('/tmp')
            with self.assertRaisesRegex(ValueError, 'unsafe file type'):
                b.cleanup_host_fixture(d, root, 'a'*16, 'owner-token', worker_stopped=True)
            self.assertTrue((d/'cache'/'part').exists())
            (d/'cache'/'escape').unlink()
            with self.assertRaisesRegex(ValueError, 'worker termination'):
                b.cleanup_host_fixture(d, root, 'a'*16, 'owner-token', worker_stopped=False)
            with self.assertRaisesRegex(ValueError, 'owner/run identity'):
                b.cleanup_host_fixture(d, root, 'a'*16, 'wrong', worker_stopped=True)
            self.assertTrue(d.exists())

    def test_cleanup_preserves_evidence_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = self.make_fixture(root)
            (d/'evidence').mkdir()
            (d/'evidence'/'trace').write_text('keep')
            with self.assertRaisesRegex(ValueError, 'evidence present'):
                b.cleanup_host_fixture(d, root, 'a'*16, 'owner-token', worker_stopped=True)
            self.assertTrue((d/'evidence'/'trace').exists())

    def test_only_owned_subprocess_group_is_stopped(self):
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
        try:
            self.assertEqual(b.stop_owned_process(proc), 'STOPPED_OWNED_GROUP')
            self.assertIsNotNone(proc.poll())
        finally:
            if proc.poll() is None: proc.kill()

    def test_host_supervisor_aborts_on_stale_and_monitor_failure(self):
        safe_resources = lambda: dict(cpu_c=44, gpu_c=42, mem_available=2*b.GIB,
            data_free=4*b.GIB, memory_oom_events=0, gpu_errors=0,
            heartbeat_age=0.1, quota_breached=False, foreign_process=False,
            operator_abort=False, connection_alive=True)
        for provider, label in [(lambda: self.sample(0), 'TELEMETRY_STALE'),
                                (lambda: (_ for _ in ()).throw(RuntimeError('lost')), 'MONITOR_FAILURE_RuntimeError')]:
            proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
            try:
                result = b.supervise_host_worker(proc, provider, safe_resources, max_seconds=1)
                self.assertEqual(result['decision'], 'ABORTED_HOST_FIXTURE')
                self.assertIn(label, result['reasons'])
                self.assertIsNotNone(proc.poll())
            finally:
                if proc.poll() is None: proc.kill()

    def test_host_supervisor_timeout(self):
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
        try:
            result = b.supervise_host_worker(proc, lambda: self.sample(b.time.monotonic()-0.02),
                lambda: dict(cpu_c=44, gpu_c=42, mem_available=2*b.GIB,
                data_free=4*b.GIB, memory_oom_events=0, gpu_errors=0,
                heartbeat_age=0.1, quota_breached=False, foreign_process=False,
                operator_abort=False, connection_alive=True),
                max_seconds=0.1, poll_interval=0.02)
            self.assertIn('COMPILER_TIMEOUT', result['reasons'])
        finally:
            if proc.poll() is None: proc.kill()


if __name__ == '__main__': unittest.main()
