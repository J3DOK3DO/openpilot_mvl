"""Synthetic signature, provenance and missing-output rejection tests. No device access."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from tools.release import qcom_b3_reuse as reuse
from tools.release import mvl_model_artifacts as model


class ReuseTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.candidates = self.root / 'candidates'
        self.evidence = self.root / 'evidence'
        self.candidates.mkdir()
        self.evidence.mkdir()
        self.graph_files = {'openpilot/selfdrive/modeld/SConscript': 'a' * 64,
                            'tinygrad_repo/tinygrad/engine/jit.py': 'b' * 64}
        self.policy = {
            'source_commit': '4' * 40, 'tinygrad_commit': '9' * 40,
            'agnos_image_sha256': '8' * 64, 'flags': 'DEV=QCOM',
            'agnos_version': '19.9', 'source_graph_file_count': len(self.graph_files),
            'source_graph_sha256': reuse.sha_bytes(reuse.canonical(self.graph_files)),
            'required_artifacts': list(model.ARTIFACTS),
            'onnx_sha256': {'driving_supercombo.onnx': '1' * 64},
            'recipe_sha256': {'SConscript': '2' * 64},
            'trusted_signers': {'producer': {}, 'reviewer': {}},
        }
        self.producer_key = Ed25519PrivateKey.generate()
        self.reviewer_key = Ed25519PrivateKey.generate()
        for name, key in [('producer', self.producer_key), ('reviewer', self.reviewer_key)]:
            pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            self.policy['trusted_signers'][name][name] = base64.b64encode(pub).decode()
        self.artifacts = {}
        for name in model.ARTIFACTS:
            payload = ('synthetic-' + name).encode()
            (self.candidates / name).write_bytes(payload)
            logs = {}
            for kind in reuse.EVIDENCE_KINDS:
                filename = name.removesuffix('.pkl') + '-' + kind + '.txt'
                body = (name + ' ' + kind + ' evidence fixture').encode()
                (self.evidence / filename).write_bytes(body)
                logs[kind] = {'file': filename, 'sha256': reuse.sha_bytes(body)}
            self.artifacts[name] = {'sha256': reuse.sha_bytes(payload),
                                    'bytes': len(payload), 'evidence': logs}
        self.capture = {
            'signer_id': 'producer', 'frozen_source_commit': self.policy['source_commit'],
            'producer_source_commit': '3' * 40,
            'tinygrad_commit': self.policy['tinygrad_commit'],
            'agnos_image_sha256': self.policy['agnos_image_sha256'],
            'agnos_version': '19.9', 'flags': 'DEV=QCOM',
            'onnx_sha256': self.policy['onnx_sha256'],
            'recipe_sha256': self.policy['recipe_sha256'],
            'source_graph_sha256': self.policy['source_graph_sha256'],
            'target_hardware': 'COMMA4', 'gpu_backend': 'QCOM',
            'artifacts': self.artifacts,
        }
        self.review = {
            'signer_id': 'reviewer',
            'capture_sha256': reuse.sha_bytes(reuse.canonical(self.capture)),
            'source_graph_sha256': self.policy['source_graph_sha256'],
            'conclusion': 'PASS_INDEPENDENT_COMPATIBILITY_AND_NATIVE_EVIDENCE',
            'source_equivalence_verified': True,
            'native_qcom_compilation_verified': True,
            'target_runtime_abi_verified': True,
            'six_model_inference_verified': True,
            'abort_power_thermal_evidence_verified': True,
        }
        self.graph = self.root / 'graph.json'
        self.capture_file = self.root / 'capture.json'
        self.review_file = self.root / 'review.json'
        self.capture_sig = self.root / 'capture.sig'
        self.review_sig = self.root / 'review.sig'
        self.graph.write_text(json.dumps({'files': self.graph_files}))
        self.persist_signatures()

    def persist_signatures(self):
        self.capture_file.write_text(json.dumps(self.capture))
        self.review_file.write_text(json.dumps(self.review))
        self.capture_sig.write_bytes(base64.b64encode(self.producer_key.sign(reuse.canonical(self.capture))))
        self.review_sig.write_bytes(base64.b64encode(self.reviewer_key.sign(reuse.canonical(self.review))))

    def qcom_fixture(self, file):
        content = file.read_bytes()
        return {'sha256': reuse.sha_bytes(content), 'size': len(content)}

    def evaluate(self):
        with patch.object(model, 'qcom_capture', self.qcom_fixture):
            return reuse.assess_signed_reuse(self.candidates, self.evidence,
                self.capture_file, self.capture_sig, self.review_file,
                self.review_sig, self.graph, self.policy)

    def test_valid_synthetic_pair_eligible_not_admitted(self):
        result = self.evaluate()
        self.assertEqual(result['signed_candidate_count'], 6)
        self.assertEqual(result['decision'], 'ELIGIBLE_FOR_SEPARATE_B3_REUSE_ACCEPTANCE')
        self.assertEqual(result['b3_verified_artifact_count'], 0)
        self.assertFalse(result['install_allowed'])

    def test_absent_signers_denied(self):
        self.policy['trusted_signers']['producer'].clear()
        with self.assertRaisesRegex(ValueError, 'no authorized'):
            self.evaluate()

    def test_missing_sixth_artifact_denied(self):
        (self.candidates / model.ARTIFACTS[1]).unlink()
        with self.assertRaisesRegex(ValueError, 'six exact'):
            self.evaluate()

    def test_extra_artifact_denied(self):
        (self.candidates / 'unexpected.pkl').write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'six exact'):
            self.evaluate()

    def test_tampered_artifact_denied(self):
        (self.candidates / model.ARTIFACTS[0]).write_bytes(b'edited')
        with self.assertRaisesRegex(ValueError, 'captured artifact bytes'):
            self.evaluate()

    def test_tampered_input_graph_denied(self):
        graph = json.loads(self.graph.read_text())
        graph['files']['openpilot/selfdrive/modeld/SConscript'] = '0' * 64
        self.graph.write_text(json.dumps(graph))
        with self.assertRaisesRegex(ValueError, 'source dependency graph differs'):
            self.evaluate()

    def test_wrong_tinygrad_sha_denied_even_if_signed(self):
        self.capture['tinygrad_commit'] = 'f' * 40
        self.persist_signatures()
        with self.assertRaisesRegex(ValueError, 'pinned compile input mismatch'):
            self.evaluate()

    def test_unsigned_capture_change_denied(self):
        self.capture['producer_source_commit'] = 'e' * 40
        self.capture_file.write_text(json.dumps(self.capture))
        with self.assertRaisesRegex(ValueError, 'producer signature'):
            self.evaluate()

    def test_same_public_key_for_two_roles_denied(self):
        self.policy['trusted_signers']['reviewer']['reviewer'] = self.policy['trusted_signers']['producer']['producer']
        self.review_sig.write_bytes(base64.b64encode(self.producer_key.sign(reuse.canonical(self.review))))
        with self.assertRaisesRegex(ValueError, 'distinct trust keys'):
            self.evaluate()

    def test_evidence_log_tamper_denied(self):
        filename = self.artifacts[model.ARTIFACTS[0]]['evidence']['compiler_log']['file']
        (self.evidence / filename).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'evidence file digest mismatch'):
            self.evaluate()

    def test_failed_independent_review_denied(self):
        self.review['six_model_inference_verified'] = False
        self.persist_signatures()
        with self.assertRaisesRegex(ValueError, 'independent review evidence incomplete'):
            self.evaluate()

    def test_symlink_evidence_denied(self):
        name = self.artifacts[model.ARTIFACTS[0]]['evidence']['compiler_log']['file']
        p = self.evidence / name
        other = self.root / 'other.txt'
        other.write_bytes(p.read_bytes())
        p.unlink()
        p.symlink_to(other)
        with self.assertRaises(OSError):
            self.evaluate()


if __name__ == '__main__':
    unittest.main()
