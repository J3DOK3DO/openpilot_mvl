import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('preflight_readonly.py')
SELECTOR = Path(__file__).with_name('release_files.py')


class ReadOnlyPreflightTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.repo = Path(self.temp.name)
    self.git('init', '-q')
    self.git('config', 'user.name', 'Offline Test')
    self.git('config', 'user.email', 'offline@example.invalid')
    release = self.repo / 'tools/release'
    release.mkdir(parents=True)
    shutil.copy2(SELECTOR, release / SELECTOR.name)
    (self.repo / 'example.txt').write_text('safe\n')
    self.commit()
    self.baseline = self.git('rev-parse', 'HEAD').stdout.strip()

  def git(self, *args):
    return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                          text=True, capture_output=True)

  def commit(self):
    self.git('add', '-A')
    self.git('commit', '-qm', 'fixture')

  def preflight(self, *args):
    result = subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.repo), *args],
                            text=True, capture_output=True)
    return result.returncode, json.loads(result.stdout)

  def test_clean_source_passes_without_modifying_repository(self):
    before = self.git('status', '--porcelain').stdout
    code, report = self.preflight('--commit', self.baseline, '--baseline', self.baseline)
    self.assertEqual(code, 0, report)
    self.assertEqual(report['result'], 'PASS')
    self.assertEqual(report['restricted_changes'], [])
    self.assertEqual(before, self.git('status', '--porcelain').stdout)

  def test_dirty_source_and_oversized_blob_hold(self):
    (self.repo / 'example.txt').write_text('changed\n')
    code, report = self.preflight('--max-blob-bytes', '1')
    self.assertEqual(code, 1)
    self.assertIn('root worktree has modified or untracked files', report['issues'])
    self.assertTrue(report['oversized_blobs'])

  def test_missing_gitlink_and_release_selector_mismatch_hold(self):
    self.git('update-index', '--add', '--cacheinfo', '160000,' + 'a' * 40 + ',panda')
    self.git('commit', '-qm', 'pinned gitlink')
    # Git may leave an empty submodule directory; it is not a checkout.
    (self.repo / 'panda').mkdir(exist_ok=True)
    code, report = self.preflight()
    self.assertEqual(code, 1)
    self.assertEqual(report['submodules'][0]['state'], 'missing')
    self.assertTrue(any('unexpanded gitlink' in issue for issue in report['issues']))

  def test_restricted_change_and_unhydrated_lfs_hold(self):
    target = self.repo / 'openpilot/selfdrive/controls/unsafe.txt'
    target.parent.mkdir(parents=True)
    target.write_text('changed\n')
    pointer = self.repo / 'asset.bin'
    pointer.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:' + 'b' * 64 + '\nsize 12\n')
    self.commit()
    code, report = self.preflight('--baseline', self.baseline)
    self.assertEqual(code, 1)
    self.assertEqual(report['restricted_changes'], ['openpilot/selfdrive/controls/unsafe.txt'])
    self.assertEqual(report['lfs_assets'][0]['state'], 'pointer_or_mismatch')


if __name__ == '__main__':
  unittest.main()
