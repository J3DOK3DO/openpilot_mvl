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
