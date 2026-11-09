import unittest
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from unittest.mock import patch

from tools.release import combined_device_gate as gate
from tools.release.combined_device_gate import evaluate, FROZEN_SOURCE, read_snapshot


GOOD = f'''AGNOS_VERSION=19.9
ARCH=aarch64
ACTIVE_COMMIT={FROZEN_SOURCE}
OFFROAD_FLAG=1
ONROAD_FLAG=0
IGNITION_FLAG=0
/sys/class/power_supply/usb/online=1
/dev/sda12 94618759168 80194441216 10000000000 90% /data
MemAvailable: 3000000 kB
crw-rw---- 1 root gpu 235, 0 Nov 9 /dev/kgsl-3d0
'''


class DeviceGateTest(unittest.TestCase):
    def test_even_good_snapshot_is_not_live_qualification(self):
        result = evaluate(GOOD)
        self.assertFalse(result['device_compile_allowed'])
        self.assertEqual(result['gates']['independent_live_parked']['status'], 'UNKNOWN')
        self.assertEqual(result['gates']['hard_quota_and_scratch_peak']['status'], 'UNKNOWN')

    def test_windows_crlf_fields_are_parsed_without_relaxing_gate(self):
        result = evaluate(GOOD.replace('\n', '\r\n'))
        self.assertEqual(result['gates']['agnos_and_arch']['status'], 'PASS')
        self.assertEqual(result['gates']['active_source_identity']['status'], 'PASS')
        self.assertEqual(result['observations']['external_supply_online_values'], ['1'])
        self.assertFalse(result['device_compile_allowed'])

    def test_negative_inputs_fail_closed(self):
        cases = [
            (GOOD.replace('ARCH=aarch64', 'ARCH=x86_64'), 'agnos_and_arch', 'FAIL'),
            (GOOD.replace('10000000000', '7000000000'), 'data_free_8gib_reserve', 'FAIL'),
            (GOOD.replace('OFFROAD_FLAG=1\n', 'OFFROAD_FLAG=1IGNITION_FLAG=UNKNOWN\n'), 'independent_live_parked', 'UNKNOWN'),
            (GOOD.replace('usb/online=1', 'usb/online=0'), 'external_sustained_power', 'FAIL'),
            (GOOD.replace(FROZEN_SOURCE, '0' * 40), 'active_source_identity', 'FAIL'),
        ]
        for raw, name, expected in cases:
            with self.subTest(name=name):
                result = evaluate(raw)
                self.assertEqual(result['gates'][name]['status'], expected)
                self.assertFalse(result['device_compile_allowed'])


class SnapshotTrustTest(unittest.TestCase):
    def test_symlink_is_rejected_before_open(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, 'target')
            target.write_text(GOOD)
            link = Path(directory, 'link')
            link.symlink_to(target)
            with patch.object(gate.os, 'open') as opened:
                with self.assertRaisesRegex(ValueError, 'non-symlink'):
                    read_snapshot(link)
            opened.assert_not_called()

    def test_special_file_is_rejected_before_open(self):
        with patch.object(gate.os, 'lstat') as lstat, patch.object(gate.os, 'open') as opened:
            lstat.return_value = os.stat_result((stat.S_IFIFO | 0o600, 1, 2, 1, 0, 0, 0, 0, 0, 0))
            with self.assertRaisesRegex(ValueError, 'regular'):
                read_snapshot(Path('never-open-this-fifo'))
            opened.assert_not_called()

    def test_inode_swap_after_lstat_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'snapshot')
            path.write_text(GOOD)
            original_open = os.open
            def swapped_open(name, flags):
                replacement = Path(directory, 'replacement')
                replacement.write_text(GOOD)
                replacement.replace(path)
                return original_open(name, flags)
            with patch.object(gate.os, 'open', side_effect=swapped_open), patch.object(gate.os, 'read') as read:
                with self.assertRaisesRegex(ValueError, 'inode changed'):
                    read_snapshot(path)
                read.assert_not_called()

    def test_growth_past_limit_is_rejected_after_bounded_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'snapshot')
            path.write_bytes(b'X')
            calls = []
            def growing_read(fd, count):
                calls.append(count)
                return b'X' * count
            with patch.object(gate.os, 'read', side_effect=growing_read):
                with self.assertRaisesRegex(ValueError, 'grew beyond'):
                    read_snapshot(path)
            self.assertEqual(sum(calls), gate.MAX_SNAPSHOT_BYTES + 1)

    def test_hash_and_parse_use_same_fd_bytes_after_path_swap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'snapshot')
            raw = ('\ufeff' + GOOD.replace('\n', '\r\n')).encode('utf-8')
            path.write_bytes(raw)
            expected = hashlib.sha256(raw).hexdigest()
            real_read = os.read
            swapped = False
            def read_then_replace(fd, count):
                nonlocal swapped
                chunk = real_read(fd, count)
                if not swapped:
                    swapped = True
                    replacement = Path(directory, 'replacement')
                    replacement.write_text('ARCH=malicious\n')
                    replacement.replace(path)
                return chunk
            stdout = io.StringIO()
            with patch.object(gate.os, 'read', side_effect=read_then_replace), \
                    patch.object(Path, 'read_bytes', side_effect=AssertionError('second open')), \
                    patch.object(sys, 'argv', ['combined_device_gate.py', str(path), '--expected-sha256', expected]), \
                    redirect_stdout(stdout):
                self.assertEqual(gate.main(), 2)
            report = json.loads(stdout.getvalue())
            self.assertEqual(report['evidence_sha256'], expected)
            self.assertEqual(report['gates']['agnos_and_arch']['status'], 'PASS')
            self.assertFalse(report['device_compile_allowed'])

    def test_hash_mismatch_and_invalid_utf8_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'snapshot')
            for data, expected in ((b'other', '0' * 64), (b'\xff', hashlib.sha256(b'\xff').hexdigest())):
                path.write_bytes(data)
                with self.subTest(data=data), patch.object(sys, 'argv', ['gate', str(path), '--expected-sha256', expected]), \
                        redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                    gate.main()
                self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
