import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from tools.release import build_qcom_handoff as handoff

class HandoffVerificationTest(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    self.payload = b'fixed-source-bytes'
    self._write_tar('safe/file.txt', self.payload)
    self._write_manifest('safe/file.txt', self.payload)

  def _write_tar(self, name, payload):
    with tarfile.open(self.root/'source.tar', 'w') as archive:
      info = tarfile.TarInfo(name)
      info.size = len(payload)
      archive.addfile(info, io.BytesIO(payload))

  def _write_manifest(self, name, payload):
    manifest = {
      'package_kind': 'SOURCE_ONLY_QCOM_HANDOFF_NOT_INSTALLABLE',
      'source_commit': '0'*40,
      'gitlinks': {str(i): 'a'*40 for i in range(7)},
      'onnx_sha256': handoff.ONNX,
      'agnos_19_8_1_image_sha256': handoff.AGNOS_SHA256,
      'required_qcom_outputs': handoff.SIX,
      'source_tar_sha256': handoff.digest(self.root/'source.tar'),
      'files': [{'path': name, 'kind': 'file', 'size':len(payload), 'sha256':hashlib.sha256(payload).hexdigest()}],
    }
    (self.root/'manifest.json').write_text(json.dumps(manifest))

  def test_valid_archive(self):
    handoff.verify(self.root)

  def test_tampered_archive_rejected(self):
    self._write_tar('safe/file.txt', b'changed-source-bytes')
    with self.assertRaisesRegex(ValueError, 'tar hash mismatch'):
      handoff.verify(self.root)

  def test_member_mismatch_rejected(self):
    self._write_manifest('other/file.txt', self.payload)
    with self.assertRaisesRegex(ValueError, 'archived path/contents differ'):
      handoff.verify(self.root)

  def test_duplicate_manifest_key_rejected(self):
    text=(self.root/'manifest.json').read_text()
    (self.root/'manifest.json').write_text('{"package_kind":"SOURCE_ONLY_QCOM_HANDOFF_NOT_INSTALLABLE",'+text[1:])
    with self.assertRaisesRegex(ValueError, 'duplicate manifest key'):
      handoff.verify(self.root)

  def test_traversal_member_rejected(self):
    self._write_tar('../escape', self.payload)
    self._write_manifest('../escape', self.payload)
    with self.assertRaisesRegex(ValueError, 'unsafe tar path'):
      handoff.verify(self.root)

if __name__=='__main__':
  unittest.main()
