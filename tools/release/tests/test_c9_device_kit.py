from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools.release import c9_device_kit as kit


ROOT = Path(__file__).resolve().parents[3]


class DeviceKitTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        for rel in kit.FILES:
            dest = self.repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / rel).read_bytes())
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=C9 Test',
                        '-c', 'user.email=c9-test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        self.output = self.root / 'kit.tar'

    def build(self):
        return kit.build(self.repo, self.output, self.root)

    def test_exact_head_manifest_and_isolated_import(self):
        result = self.build()
        head = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()
        self.assertEqual(result['engineering_head'], head)
        self.assertFalse(result['install_allowed'])
        self.assertFalse(result['execution_authorized'])
        self.assertEqual((result['b3_verified_outputs'], result['g10_product'], result['physical_checks_passed']),
                         (0, 'NOT_BUILT', 0))
        kit.verify(self.output, json.loads(self.output.with_suffix('.json').read_text()))
        extracted = self.root / 'extracted'
        extracted.mkdir()
        with tarfile.open(self.output) as archive:
            for member in archive.getmembers():
                target = extracted / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        self.assertEqual(hashlib.sha256((extracted/'tools/release/preflight_readonly.py').read_bytes()).hexdigest(),
                         kit.PREFLIGHT_SHA256)
        for row in result['files']:
            self.assertEqual((extracted/row['path']).read_bytes(),
                             subprocess.check_output(['git', '-C', str(self.repo), 'show', 'HEAD:'+row['path']]))
        code = 'from tools.release import c9_b3_pilot as p; assert p.checked_plan()["source_commit"] == p.SOURCE; print(p.TRUSTED_PREFLIGHT.is_file())'
        imported = subprocess.run([sys.executable, '-B', '-c', code], cwd=extracted,
                                  env={**os.environ, 'PYTHONPATH': str(extracted)}, capture_output=True, text=True)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(imported.stdout.strip(), 'True')
        # The pilot's read-only branch can be exercised without a Comma fixture.
        with patch('tools.release.c9_b3_pilot.preflight', return_value={
            'decision': 'READ_ONLY_PREFLIGHT_PASS_EXECUTION_NOT_AUTHORIZED'}), \
             patch('sys.argv', ['pilot', '--source', '/data/mvl-builds/'+kit.FROZEN_SOURCE+'/source',
                                '--scratch', '/data/mvl-builds/'+kit.FROZEN_SOURCE+'/scratch']):
            from tools.release import c9_b3_pilot
            self.assertEqual(c9_b3_pilot.main(), 2)

    def test_both_mandatory_helpers_and_pinned_plan_cannot_be_excluded(self):
        blobs = {rel: (ROOT/rel).read_bytes() for rel in kit.FILES}
        for removed in ('tools/release/agnos_image.py',
                        'tools/release/preflight_readonly.py',
                        'docs/engineering/autonomous_campaign/B3_SIX_TARGET_DRY_RUN_20261107.json'):
            with self.subTest(removed=removed), self.assertRaisesRegex(ValueError, 'missing mandatory'):
                kit.check_dependencies({name: data for name, data in blobs.items() if name != removed})

    def test_missing_trusted_preflight_rejected(self):
        (self.repo/'tools/release/preflight_readonly.py').unlink()
        with self.assertRaises((OSError, ValueError)):
            self.build()
        self.assertFalse(self.output.exists())

    def test_tampered_file_rejected(self):
        with (self.repo/'tools/release/c9_b3_pilot.py').open('ab') as stream:
            stream.write(b'\n# tampered\n')
        with self.assertRaisesRegex(ValueError, 'uncommitted source differences'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_symlink_and_stale_dependency_rejected(self):
        path = self.repo/'tools/release/preflight_readonly.py'
        path.unlink()
        path.symlink_to(ROOT/'tools/release/preflight_readonly.py')
        with self.assertRaisesRegex(ValueError, 'uncommitted source differences|symlink'):
            self.build()
        blobs = {rel: (ROOT/rel).read_bytes() for rel in kit.FILES}
        blobs['tools/release/c9_b3_pilot.py'] += b'\nfrom tools.release import missing_helper\n'
        with self.assertRaisesRegex(ValueError, 'stale dependency'):
            kit.check_dependencies(blobs)

    def test_deterministic_tar_and_tamper_detection(self):
        first = self.build()
        second_path = self.root/'kit2.tar'
        second = kit.build(self.repo, second_path, self.root)
        self.assertEqual(first['tar_sha256'], second['tar_sha256'])
        with self.output.open('ab') as stream:
            stream.write(b'tamper')
        self.assertNotEqual(hashlib.sha256(self.output.read_bytes()).hexdigest(), first['tar_sha256'])
        with self.assertRaisesRegex(ValueError, 'trailing data'):
            kit.verify(self.output, json.loads(self.output.with_suffix('.json').read_text()))


if __name__ == '__main__':
    unittest.main()
