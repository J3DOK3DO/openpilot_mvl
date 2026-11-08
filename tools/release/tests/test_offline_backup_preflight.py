import hashlib
import os
import tempfile
import json
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path

from tools.release import offline_backup_preflight as backup


class OfflineBackupPreflightTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'known_good').mkdir()
        (self.root / 'owner_data').mkdir()
        self.file = self.root / 'known_good' / 'package.txt'
        self.file.write_bytes(b'known good bytes')
        self.manifest = {'schema_version': 1, 'known_good_commit': backup.KNOWN_GOOD,
                         'files': [{'path': 'known_good/package.txt', 'size': 16,
                                    'sha256': hashlib.sha256(b'known good bytes').hexdigest()}]}

    def run_manifest_cli(self, path, digest):
        run = subprocess.run([sys.executable, '-B', '-m', 'tools.release.offline_backup_preflight',
                              '--root', str(self.root), '--manifest', str(path),
                              '--expected-manifest-sha256', digest],
                             text=True, capture_output=True, timeout=3)
        self.assertEqual(run.returncode, 2)
        report = json.loads(run.stdout)
        self.assertEqual(report['decision'], 'NOT_INSTALLABLE')
        self.assertIs(report['install_allowed'], False)
        return report

    def test_exact_host_copy_stays_noninstallable(self):
        result = backup.verify(self.root, self.manifest)
        self.assertEqual(result['backup_inventory'], 'HOST_COPY_BYTES_MATCH')
        self.assertFalse(result['install_allowed'])
        self.assertFalse(result['known_good_currently_installed_verified'])
        self.assertEqual(result['manifest_trust'], 'EXTERNAL_HASH_REQUIRED')

    def test_corrupt_or_incomplete_backup_rejected(self):
        self.file.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            backup.verify(self.root, self.manifest)
        self.file.write_bytes(b'known good bytes')
        (self.root / 'owner_data' / 'extra.txt').write_text('unlisted')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            backup.verify(self.root, self.manifest)

    def test_untrusted_paths_and_identity_rejected(self):
        for path in ('../known_good/package.txt', '/known_good/package.txt',
                     'known_good/../owner_data/x', 'owner_data/params/secret',
                     'known_good/panda.bin'):
            with self.subTest(path=path):
                altered = {**self.manifest, 'files': [{**self.manifest['files'][0], 'path': path}]}
                with self.assertRaises(ValueError):
                    backup.verify(self.root, altered)
        with self.assertRaisesRegex(ValueError, 'identity'):
            backup.verify(self.root, {**self.manifest, 'known_good_commit': '0' * 40})

    def test_symlink_and_duplicate_rejected(self):
        link = self.root / 'known_good' / 'link.txt'
        link.symlink_to(self.file)
        altered = {**self.manifest, 'files': [self.manifest['files'][0],
                                             {**self.manifest['files'][0], 'path': 'known_good/link.txt'}]}
        with self.assertRaisesRegex(ValueError, 'special file'):
            backup.verify(self.root, altered)
        link.unlink()
        altered = {**self.manifest, 'files': self.manifest['files'] * 2}
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            backup.verify(self.root, altered)

    def test_missing_known_good_and_capitalized_params_rejected(self):
        (self.root / 'owner_data' / 'note.txt').write_bytes(b'note')
        owner = {'path': 'owner_data/note.txt', 'size': 4,
                 'sha256': hashlib.sha256(b'note').hexdigest()}
        with self.assertRaisesRegex(ValueError, 'known-good'):
            backup.verify(self.root, {**self.manifest, 'files': [owner]})
        altered = {**self.manifest, 'files': [{**self.manifest['files'][0],
                                             'path': 'known_good/Params/key'}]}
        with self.assertRaisesRegex(ValueError, 'protected'):
            backup.verify(self.root, altered)

    def test_cli_requires_matching_manifest_digest_and_always_holds(self):
        manifest_path = self.root / 'manifest.json'
        raw = json.dumps(self.manifest).encode()
        manifest_path.write_bytes(raw)
        for digest, expected in [(hashlib.sha256(raw).hexdigest(), 'HOST_COPY_BYTES_MATCH'),
                                 ('0' * 64, 'digest mismatch')]:
            run = subprocess.run([sys.executable, '-B', '-m', 'tools.release.offline_backup_preflight',
                                  '--root', str(self.root), '--manifest', str(manifest_path),
                                  '--expected-manifest-sha256', digest],
                                 text=True, capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(json.loads(run.stdout)['install_allowed'])
            self.assertIn(expected, run.stdout)

    @unittest.skipUnless(hasattr(os, 'mkfifo') and hasattr(os, 'O_NONBLOCK') and
                         hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_CLOEXEC'),
                         'safe FIFO opening APIs unavailable')
    def test_cli_manifest_fifo_without_writer_rejected_with_timeout(self):
        fifo = self.root / 'manifest.fifo'
        os.mkfifo(fifo)
        report = self.run_manifest_cli(fifo, '0' * 64)
        self.assertIn('not a regular file', report['input_error'])

    @unittest.skipUnless(hasattr(os, 'symlink') and hasattr(os, 'O_NOFOLLOW'),
                         'symlink or nofollow API unavailable')
    def test_cli_manifest_symlink_rejected_even_with_matching_digest(self):
        target = self.root / 'actual.json'
        raw = json.dumps(self.manifest).encode()
        target.write_bytes(raw)
        link = self.root / 'manifest.json'
        link.symlink_to(target)
        report = self.run_manifest_cli(link, hashlib.sha256(raw).hexdigest())
        self.assertIn('not a regular file', report['input_error'])

    def test_cli_manifest_directory_type_mismatch_rejected(self):
        report = self.run_manifest_cli(self.root / 'known_good', '0' * 64)
        self.assertIn('not a regular file', report['input_error'])

    def test_cli_manifest_oversize_and_regular_success_stay_on_hold(self):
        path = self.root / 'manifest.json'
        raw = b' ' * (backup._MAX_MANIFEST_BYTES + 1)
        path.write_bytes(raw)
        report = self.run_manifest_cli(path, hashlib.sha256(raw).hexdigest())
        self.assertIn('exceeds size limit', report['input_error'])
        raw = json.dumps(self.manifest).encode()
        path.write_bytes(raw)
        report = self.run_manifest_cli(path, hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['backup_inventory'], 'HOST_COPY_BYTES_MATCH')
        self.assertEqual(report['manifest_trust'], 'EXTERNAL_HASH_REQUIRED')

    def test_manifest_inode_swap_after_lstat_rejected(self):
        path = self.root / 'manifest.json'
        path.write_bytes(b'first')
        replacement = self.root / 'replacement.json'
        replacement.write_bytes(b'second')
        original_open = backup.os.open

        def swap_on_open(name, flags, *args, **kwargs):
            if name == path:
                replacement.replace(path)
            return original_open(name, flags, *args, **kwargs)

        with mock.patch.object(backup.os, 'open', side_effect=swap_on_open):
            with self.assertRaisesRegex(ValueError, 'changed'):
                backup._read_manifest(path)

    def test_manifest_changed_bytes_on_held_fd_rejected(self):
        path = self.root / 'manifest.json'
        path.write_bytes(b'first')
        original_read = backup.os.read

        def change_on_read(fd, count):
            data = original_read(fd, count)
            if data:
                path.write_bytes(b'other')
            return data

        with mock.patch.object(backup.os, 'read', side_effect=change_on_read):
            with self.assertRaisesRegex(ValueError, 'changed'):
                backup._read_manifest(path)

    @unittest.skipUnless(hasattr(os, 'mkfifo') and hasattr(os, 'O_NOFOLLOW') and
                         hasattr(os, 'O_NONBLOCK') and hasattr(os, 'O_CLOEXEC'),
                         'nonblocking FIFO API required for bounded race test')
    def test_manifest_regular_to_fifo_swap_after_lstat_cannot_block(self):
        path = self.root / 'manifest.json'
        path.write_bytes(b'original')
        script = "\n".join([
            "import os, sys",
            "from pathlib import Path",
            "from unittest import mock",
            "from tools.release import offline_backup_preflight as backup",
            "p = Path(sys.argv[1])",
            "saved = backup.os.open",
            "def change(name, flags, *args, **kw):",
            "    if name == p:",
            "        p.unlink()",
            "        os.mkfifo(p)",
            "    return saved(name, flags, *args, **kw)",
            "with mock.patch.object(backup.os, 'open', side_effect=change):",
            "    try:",
            "        backup._read_manifest(p)",
            "    except ValueError as e:",
            "        sys.exit(0 if 'changed' in str(e) or 'unsafe' in str(e) else 3)",
            "sys.exit(2)",
        ])
        run = subprocess.run([sys.executable, '-B', '-c', script, str(path)],
                             cwd=Path(__file__).resolve().parents[3],
                             text=True, capture_output=True, timeout=3)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_external_hardlink_is_not_a_self_contained_backup(self):
        outside = self.root.parent / (self.root.name + '-outside')
        outside.write_bytes(b'known good bytes')
        self.addCleanup(outside.unlink)
        self.file.unlink()
        os.link(outside, self.file)
        with self.assertRaisesRegex(ValueError, 'hardlink'):
            backup.verify(self.root, self.manifest)

    def test_unlisted_fifo_is_rejected_without_opening_it_blocking(self):
        os.mkfifo(self.root / 'owner_data' / 'unexpected_fifo')
        original_open = backup.os.open
        def reject_fifo_open(path, flags, *args, **kwargs):
            if path == 'unexpected_fifo':
                self.fail('special file was opened before type validation')
            return original_open(path, flags, *args, **kwargs)
        with mock.patch.object(backup.os, 'open', side_effect=reject_fifo_open):
            with self.assertRaisesRegex(ValueError, 'special file'):
                backup.verify(self.root, self.manifest)

    def test_unlisted_empty_directory_is_rejected(self):
        (self.root / 'owner_data' / 'unlisted_empty').mkdir()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            backup.verify(self.root, self.manifest)

    def test_replacement_by_symlink_between_stat_and_open_is_rejected(self):
        outside = self.root.parent / (self.root.name + '-outside')
        outside.write_bytes(b'known good bytes')
        self.addCleanup(outside.unlink)
        original_open = backup.os.open
        swapped = False

        def replace_on_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == 'package.txt' and not swapped:
                swapped = True
                self.file.unlink()
                self.file.symlink_to(outside)
            return original_open(path, flags, *args, **kwargs)

        with mock.patch.object(backup.os, 'open', side_effect=replace_on_open):
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                backup.verify(self.root, self.manifest)
        self.assertTrue(swapped)

    def test_duplicate_json_keys_fail_closed(self):
        manifest_path = self.root / 'manifest.json'
        raw = b'{"schema_version":1,"schema_version":1,"known_good_commit":"' + backup.KNOWN_GOOD.encode() + b'","files":[]}'
        manifest_path.write_bytes(raw)
        run = subprocess.run([sys.executable, '-B', '-m', 'tools.release.offline_backup_preflight',
                              '--root', str(self.root), '--manifest', str(manifest_path),
                              '--expected-manifest-sha256', hashlib.sha256(raw).hexdigest()],
                             text=True, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertIn('duplicate backup manifest key', run.stdout)

    def test_oversized_manifest_fails_before_parse(self):
        manifest_path = self.root / 'manifest.json'
        raw = b' ' * (backup._MAX_MANIFEST_BYTES + 1)
        manifest_path.write_bytes(raw)
        run = subprocess.run([sys.executable, '-B', '-m', 'tools.release.offline_backup_preflight',
                              '--root', str(self.root), '--manifest', str(manifest_path),
                              '--expected-manifest-sha256', hashlib.sha256(raw).hexdigest()],
                             text=True, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertIn('exceeds size limit', run.stdout)
