import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools.release import c19_acceptance as c19
from tools.release import c19_build_package as c19_build


class TestC19Acceptance(unittest.TestCase):
  def test_constants_pin_accepted_candidate(self):
    self.assertEqual(c19.ARCHIVE_SHA256, "449624da60c90fdc667740c08153622d6d0ec721f0adaef1e7508ba181b57634")
    self.assertEqual(c19.LOCAL_TREE, "14ba8c869c9383fa2aa27caf6fb8fcd4b557b23e")

  def test_offline_verifies_explicit_c18_object_not_current_head(self):
    source = Path(c19.__file__).read_text()
    self.assertIn('git("rev-parse", f"{LOCAL_COMMIT}^{{tree}}")', source)
    self.assertIn('"c19_local_commit": c19_head', source)
    self.assertNotIn('(local_head, local_tree, source_head)', source)

  def test_remediated_builder_retains_non_installable_classification(self):
    source = Path(c19_build.__file__).read_text()
    self.assertIn('"classification": "NATIVE_UI_OFFLINE_CANDIDATE"', source)
    self.assertIn('"install_allowed": False, "actuation_allowed": False', source)
    self.assertIn("relative-import closure remediation is absent", source)
    self.assertIn("28ac276b04977cad336b74785e7cf0bccd0efb098c7495e974c0cad9382b4173", source)
    self.assertIn("TERM-to-KILL watchdog escalation", source)

  def test_hold_records_never_claim_physical_evidence(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      c19.hold_records(root)
      authorization = json.loads((root / "C19_DEVICE_AUTHORIZATION.json").read_text())
      isolation = json.loads((root / "C19_PHYSICAL_ISOLATION_EVIDENCE.json").read_text())
      self.assertEqual(authorization["status"], "NOT_RUN")
      self.assertFalse(authorization["authorization_received"])
      self.assertFalse(isolation["physical_isolation_witnessed"])
      self.assertNotIn("physical_isolation_verified", authorization)

  def test_archive_audit_rejects_link(self):
    with tempfile.TemporaryDirectory() as temporary:
      candidate = Path(temporary) / "candidate.tar.gz"
      with tarfile.open(candidate, "w:gz") as archive:
        link = tarfile.TarInfo(c19.PREFIX + "escape")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../escape"
        archive.addfile(link)
      with patch.object(c19, "ARCHIVE", candidate), patch.object(c19, "ARCHIVE_SHA256", c19.digest(candidate)):
        with self.assertRaisesRegex(ValueError, "unsafe archive member"):
          c19.archive_audit()

  def test_archive_audit_rejects_hash_mismatch(self):
    with tempfile.TemporaryDirectory() as temporary:
      candidate = Path(temporary) / "candidate.tar.gz"
      manifest = {"files": {"payload": {"bytes": 3, "sha256": "0" * 64}}}
      with tarfile.open(candidate, "w:gz") as archive:
        for name, data in (("MANIFEST.json", json.dumps(manifest).encode()), ("payload", b"abc")):
          info = tarfile.TarInfo(c19.PREFIX + name)
          info.size = len(data)
          archive.addfile(info, io.BytesIO(data))
      with patch.object(c19, "ARCHIVE", candidate), patch.object(c19, "ARCHIVE_SHA256", c19.digest(candidate)):
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
          c19.archive_audit()


if __name__ == "__main__":
  unittest.main()
