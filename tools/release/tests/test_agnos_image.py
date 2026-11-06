import hashlib
import json
import lzma
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.release import agnos_image


def sha(data):
    return hashlib.sha256(data).hexdigest()


class AgnosImageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.compressed = self.root / 'system.img.xz'
        self.output = self.root / 'system.img'
        self.manifest = self.root / 'agnos.json'
        self.raw = b'abcdQWER\0\0\0\0'
        self.sparse = (agnos_image.HEADER.pack(agnos_image.MAGIC, 1, 0, 28, 12, 4, 3, 3, 0)
                       + agnos_image.CHUNK.pack(agnos_image.RAW, 0, 1, 16) + b'abcd'
                       + agnos_image.CHUNK.pack(agnos_image.FILL, 0, 1, 16) + b'QWER'
                       + agnos_image.CHUNK.pack(agnos_image.DONT_CARE, 0, 1, 12))
        self.compressed.write_bytes(lzma.compress(self.sparse))
        self.set_manifest()

    def set_manifest(self, **changes):
        part = {'name': 'system', 'sparse': True, 'size': len(self.raw),
                'hash': sha(self.sparse), 'hash_raw': sha(self.raw)}
        part.update(changes)
        self.manifest.write_text(json.dumps([part]))
        self.anchor = agnos_image.digest_file(self.manifest)

    def test_reconstructs_and_verifies_both_hashes(self):
        result = agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertEqual(result['verification'], 'PASS_SPARSE_AND_RAW_HASH')
        self.assertEqual(self.output.read_bytes(), self.raw)

    def test_bad_raw_hash_rejected_and_partial_removed(self):
        self.set_manifest(hash_raw='0' * 64)
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_name(self.output.name + '.partial').exists())

    def test_manifest_requires_external_anchor(self):
        with self.assertRaisesRegex(ValueError, 'external SHA-256 anchor'):
            agnos_image.reconstruct(self.compressed, self.output, self.manifest, '0' * 64)

    def test_truncated_sparse_input_rejected(self):
        self.compressed.write_bytes(lzma.compress(self.sparse[:-1]))
        with self.assertRaises(ValueError):
            agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertFalse(self.output.exists())

    def test_existing_output_refused(self):
        self.output.write_bytes(b'existing')
        with self.assertRaisesRegex(ValueError, 'output exists'):
            agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertEqual(self.output.read_bytes(), b'existing')

    def test_output_created_during_reconstruction_is_not_overwritten(self):
        real_link = agnos_image.publish_open_file
        def racing_link(fd, dst):
            dst.write_bytes(b'other process')
            return real_link(fd, dst)
        with patch.object(agnos_image, 'publish_open_file', side_effect=racing_link):
            with self.assertRaises(FileExistsError):
                agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertEqual(self.output.read_bytes(), b'other process')
        self.assertFalse(self.output.with_name(self.output.name + '.partial').exists())

    def test_preexisting_partial_is_preserved(self):
        partial = self.output.with_name(self.output.name + '.partial')
        partial.write_bytes(b'other process')
        with self.assertRaisesRegex(ValueError, 'partial output already exists'):
            agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertEqual(partial.read_bytes(), b'other process')

    def test_reported_compressed_hash_is_from_opened_input(self):
        original = self.compressed.read_bytes()
        real_link = agnos_image.publish_open_file
        def replace_input_then_link(fd, dst):
            self.compressed.unlink()
            self.compressed.write_bytes(b'replacement')
            return real_link(fd, dst)
        with patch.object(agnos_image, 'publish_open_file', side_effect=replace_input_then_link):
            result = agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertEqual(result['compressed_sha256'], sha(original))
        self.assertEqual(result['compressed_bytes'], len(original))
        self.assertEqual(self.output.read_bytes(), self.raw)

    def test_replaced_partial_cannot_change_published_bytes(self):
        real_link = agnos_image.publish_open_file
        partial = self.output.with_name(self.output.name + '.partial')
        def replace_partial_then_link(fd, dst):
            partial.unlink()
            partial.write_bytes(b'BAD!')
            return real_link(fd, dst)
        with patch.object(agnos_image, 'publish_open_file', side_effect=replace_partial_then_link):
            with self.assertRaises(FileNotFoundError):
                agnos_image.reconstruct(self.compressed, self.output, self.manifest, self.anchor)
        self.assertFalse(self.output.exists())
        self.assertEqual(partial.read_bytes(), b'BAD!')

    def test_manifest_is_parsed_from_hashed_bytes(self):
        original = self.manifest.read_bytes()
        real_fdopen = agnos_image.os.fdopen
        def replace_manifest_after_open(fd, mode):
            stream = real_fdopen(fd, mode)
            if mode == 'rb' and self.manifest.exists():
                self.manifest.unlink()
                self.manifest.write_bytes(b'[]')
            return stream
        with patch.object(agnos_image.os, 'fdopen', side_effect=replace_manifest_after_open):
            part = agnos_image.pinned_system(self.manifest, self.anchor)
        self.assertEqual(part['hash_raw'], sha(self.raw))
        self.assertNotEqual(sha(self.manifest.read_bytes()), sha(original))

    def test_duplicate_manifest_key_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate manifest key'):
            agnos_image.unique_pairs([('size', 1), ('size', 2)])


if __name__ == '__main__':
    unittest.main()
