from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools.release import inspect_native_product as inspector

class NativeProductInspectorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.stage = Path(self.tmp.name) / 'stage'
        self.stage.mkdir()
        self.source = Path.cwd()
        self.head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        self.manifest = Path(self.tmp.name) / 'missing-qcom-manifest.json'

    def test_documented_cli_invocation_imports(self):
        command = subprocess.run(['python3', 'tools/release/inspect_native_product.py', '--help'], capture_output=True, text=True)
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertIn('--staging-root', command.stdout)

    def test_x86_binary_and_missing_qcom_remain_hold(self):
        shutil.copy2('/bin/true', self.stage / 'native-binary')
        report = inspector.inspect(self.source, self.stage, self.manifest, self.head)
        self.assertEqual(report['static_decision'], 'HOLD_STATIC_ISSUES')
        self.assertEqual(report['device_qualification'], 'NOT_TESTED')
        self.assertEqual(report['elf_count'], 1)
        self.assertTrue(any('non-AArch64 ELF' in issue for issue in report['issues']))
        self.assertTrue(any('missing stock QCOM output' in issue for issue in report['issues']))

    def test_escaping_symlink_reported(self):
        (self.stage / 'escape').symlink_to('/etc/passwd')
        report = inspector.inspect(self.source, self.stage, self.manifest, self.head)
        self.assertTrue(any('escaping symlink' in issue for issue in report['issues']))
        self.assertEqual(report['file_count'], 1)

    def test_wrong_source_commit_rejected(self):
        with self.assertRaisesRegex(ValueError, 'source checkout differs'):
            inspector.inspect(self.source, self.stage, self.manifest, '0' * 40)

    def test_dirty_source_rejected(self):
        marker = self.source / 'mvl-inspector-dirty-source-test.py'
        try:
            marker.write_text('dirty')
            with self.assertRaisesRegex(ValueError, 'not clean'):
                inspector.inspect(self.source, self.stage, self.manifest, self.head)
        finally:
            marker.unlink(missing_ok=True)

    def test_duplicate_manifest_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate manifest key'):
            inspector.unique_pairs([('source_commit', 'a'), ('source_commit', 'b')])

    def test_agnos_199_contract_rejects_cross_version_substitution(self):
        from tools.release.mvl_model_artifacts import AGNOS199_IMAGE_SHA256, AGNOS199_MANIFEST_SHA256
        manifest = {'source_commit': self.head, 'agnos': {'version': '19.9',
                    'image_sha256': AGNOS199_IMAGE_SHA256,
                    'component_manifest_sha256': AGNOS199_MANIFEST_SHA256}, 'artifacts': {}}
        self.manifest.write_text(json.dumps(manifest))
        def git_output(argv, **kwargs):
            return self.head + '\n' if argv[-2:] == ['rev-parse', 'HEAD'] else ''
        with patch.object(inspector.subprocess, 'check_output', side_effect=git_output):
            ok = inspector.inspect(self.source, self.stage, self.manifest, self.head, '19.9')
            wrong = inspector.inspect(self.source, self.stage, self.manifest, self.head, '19.8.1')
        self.assertFalse(any('AGNOS identity mismatch' in x for x in ok['issues']))
        self.assertTrue(any('AGNOS identity mismatch' in x for x in wrong['issues']))

if __name__ == '__main__':
    unittest.main()
