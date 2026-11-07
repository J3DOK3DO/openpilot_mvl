import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from tools.release import campaign2_host_guardian as g


class HostGuardianTest(unittest.TestCase):
    def fixture(self, directory: Path, seconds: float = 4) -> Path:
        script = directory / 'worker.py'
        script.write_text(f'import time\nfrom pathlib import Path\ntime.sleep({seconds})\nPath("completed").write_text("yes")\n')
        return script

    def test_worker_exit_and_timeout_are_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fast = g.start_host_fixture(directory, self.fixture(directory, 0.05),
                                        max_seconds=2, heartbeat_seconds=0.5)
            self.assertEqual(fast.result()['reason'], 'EXIT_ZERO')
            self.assertEqual(json.loads((directory/'guardian_result.json').read_text())['decision'],
                             'HOST_FIXTURE_EXITED')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            slow = g.start_host_fixture(directory, self.fixture(directory),
                                        max_seconds=0.3, heartbeat_seconds=0.2)
            while slow.process.is_alive() and not (directory/'guardian_result.json').exists():
                try: slow.heartbeat()
                except (BrokenPipeError, OSError): break
                time.sleep(0.04)
            self.assertEqual(slow.result()['reason'], 'TIMEOUT')
            self.assertFalse((directory/'completed').exists())

    def test_lost_heartbeat_and_controller_disconnect_abort(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            handle = g.start_host_fixture(directory, self.fixture(directory),
                                          max_seconds=2, heartbeat_seconds=0.15)
            self.assertEqual(handle.result()['reason'], 'HEARTBEAT_LOST')
            self.assertFalse((directory/'completed').exists())
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            handle = g.start_host_fixture(directory, self.fixture(directory),
                                          max_seconds=2, heartbeat_seconds=0.5)
            handle.connection.close()
            handle.process.join(timeout=2)
            self.assertFalse(handle.process.is_alive())
            self.assertEqual(json.loads((directory/'guardian_result.json').read_text())['reason'],
                             'CONTROLLER_DISCONNECTED')
            self.assertFalse((directory/'completed').exists())

    def test_explicit_abort_and_invalid_path_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'beneath /tmp'):
            g.start_host_fixture(Path('/data/openpilot'), Path('/data/openpilot/worker.py'))
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            handle = g.start_host_fixture(directory, self.fixture(directory),
                                          max_seconds=2, heartbeat_seconds=0.5)
            handle.abort()
            self.assertEqual(handle.result()['reason'], 'ABORT_OR_INVALID_COMMAND')
            self.assertFalse((directory/'completed').exists())

    def test_guardian_death_kills_single_worker_leader(self):
        if sys.platform != 'linux': self.skipTest('Linux parent-death signal fixture')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            handle = g.start_host_fixture(directory, self.fixture(directory),
                                          max_seconds=4, heartbeat_seconds=1)
            handle.process.kill()
            handle.process.join(timeout=2)
            self.assertFalse(handle.process.is_alive())
            for _ in range(30):
                try:
                    stat = Path(f'/proc/{handle.worker_pid}/stat').read_text().split()
                    if stat[2] == 'Z': break
                except FileNotFoundError:
                    break
                time.sleep(0.03)
            else:
                self.fail('single fixture worker remained running after guardian death')
            self.assertFalse((directory/'completed').exists())


if __name__ == '__main__': unittest.main()
