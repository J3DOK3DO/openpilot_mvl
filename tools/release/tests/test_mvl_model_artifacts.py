import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.release import mvl_model_artifacts as m


def short_string(value):
    data = value.encode()
    return b'\x8c' + bytes([len(data)]) + data


def capture(*, backend='QCOM', model=False):
    code = b'\x80\x04'
    for name in ('_TinyJit', 'CapturedJit'):
        code += short_string('tinygrad.engine.jit') + short_string(name) + b'\x93\x30'
    code += b'\x5d'
    labels = ['metadata', 'run', 'input_specs', backend]
    if model:
        labels += ['output_specs', 'output_slices', 'input_shapes']
    for label in labels:
        code += short_string(label) + b'\x61'
    code += b'.'
    return len(code).to_bytes(8, 'little', signed=True) + code + b'out-of-band-buffer'


class ModelArtifactPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source'
        self.assets = self.base / 'assets'
        self.artifacts = self.base / 'artifacts'
        self.agnos = self.base / 'agnos'
        for directory in (self.source, self.assets, self.artifacts, self.agnos):
            directory.mkdir()
        for name in m.SOURCE_FILES:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        for part in m.COMPILER_DIRS:
            path = self.source / 'tinygrad_repo' / part / 'compiler.py'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(part)
        models = self.source / m.MODEL_DIR
        models.mkdir(parents=True)
        for name in m.ONNX:
            data = (name * 3).encode()
            digest = hashlib.sha256(data).hexdigest()
            (models / name).write_text(f'{m.LFS_HEADER}\noid sha256:{digest}\nsize {len(data)}\n')
            (self.assets / name).write_bytes(data)
        for name in m.ARTIFACTS:
            (self.artifacts / name).write_bytes(capture(model=name in m.ARTIFACTS[:2]))
        (self.agnos / 'VERSION').write_text('19.8.1\n')
        (self.agnos / 'AGNOS').write_bytes(b'')
        self.image = self.base / 'agnos.ext4'
        self.image.write_bytes(b'isolated test image')
        self.image_patch = patch.object(m, 'AGNOS_SHA256', hashlib.sha256(self.image.read_bytes()).hexdigest())
        self.image_patch.start()
        self.addCleanup(self.image_patch.stop)
        self.git_patch = patch.object(m, 'source_identity', return_value=('a' * 40, 'b' * 40))
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)

    def check(self):
        return m.inventory(self.source, self.assets, self.artifacts, self.image, self.agnos)

    def test_valid_static_inventory_binds_all_six(self):
        result = self.check()
        self.assertEqual(set(result['artifacts']), set(m.ARTIFACTS))
        self.assertEqual(result['source_commit'], 'a' * 40)
        self.assertEqual(result['agnos']['version'], '19.8.1')

    def test_cpu_artifact_rejected(self):
        (self.artifacts / m.ARTIFACTS[2]).write_bytes(capture(backend='CPU:LLVM'))
        with self.assertRaisesRegex(ValueError, 'QCOM'):
            self.check()

    def test_onnx_hash_mismatch_rejected(self):
        (self.assets / m.ONNX[0]).write_bytes(b'bad bytes')
        with self.assertRaisesRegex(ValueError, 'ONNX bytes differ'):
            self.check()

    def test_missing_or_extra_artifact_rejected(self):
        (self.artifacts / m.ARTIFACTS[-1]).unlink()
        with self.assertRaisesRegex(ValueError, 'non-regular'):
            self.check()
        (self.artifacts / m.ARTIFACTS[-1]).write_bytes(capture())
        (self.artifacts / 'unexpected.pkl').write_bytes(capture())
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            self.check()

    def test_symlink_artifact_rejected(self):
        target = self.artifacts / m.ARTIFACTS[-1]
        target.unlink()
        target.symlink_to(self.artifacts / m.ARTIFACTS[0])
        with self.assertRaisesRegex(ValueError, 'non-regular'):
            self.check()

    def test_agnos_and_source_identity_bound(self):
        (self.agnos / 'VERSION').write_text('19.8.0')
        with self.assertRaisesRegex(ValueError, '19.8.1'):
            self.check()
        (self.agnos / 'VERSION').write_text('19.8.1')
        before = self.check()
        (self.source / m.SOURCE_FILES[0]).write_text('changed compiler recipe')
        self.assertNotEqual(before['source_files'], self.check()['source_files'])

    def test_wrong_agnos_image_rejected(self):
        self.image.write_bytes(b'not the pinned reference')
        with self.assertRaisesRegex(ValueError, 'AGNOS image differs'):
            self.check()

    def test_duplicate_manifest_key_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            m.no_duplicate_keys([('version', 1), ('version', 1)])


if __name__ == '__main__':
    unittest.main()
