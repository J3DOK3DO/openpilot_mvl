import copy
import io
import json
import os
import tempfile
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.release import mvl_model_artifacts as model
from tools.release import qcom_b3_admission as admission
from tools.release import qcom_b3_prepare as prep


def plan():
    return admission.trusted_plan()


def fabricated_records():
    return [{
        'artifact': name, 'source_commit': prep.SOURCE,
        'tinygrad_commit': prep.TINYGRAD,
        'agnos_image_sha256': model.AGNOS199_IMAGE_SHA256,
        'compiler_exit_code': 0, 'gpu_backend': 'QCOM',
        'sha256': f'{index:064x}', 'bytes': 128,
        'elapsed_seconds': 1, 'peak_rss_bytes': 1024,
        'quality_result': 'PASS_INDEPENDENT_REVIEW',
        **{field: '0' * 64 for field in admission.REQUIRED_EVIDENCE},
    } for index, name in enumerate(model.ARTIFACTS, 1)]


class AdmissionTest(unittest.TestCase):
    def test_prepared_is_not_safety_approval(self):
        result = admission.audit(plan(), [])
        self.assertEqual(result['decision'], 'PREPARED_NO_QCOM_DEVICE')
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['b3_verified_artifact_count'], 0)
        self.assertEqual(result['b2_safety_status'], 'NOT_SAFETY_ACCEPTED_NOT_PASSED')
        self.assertFalse(result['g10_promotion'])

    def test_every_plan_field_is_pinned(self):
        changes = [
            ('source_commit', '0' * 40), ('tinygrad_commit', '0' * 40),
            ('handoff_manifest_sha256', '0' * 64), ('qcom_flags', 'DEV=LLVM'),
            ('unset_environment', []), ('required_before_execution', []),
            ('pilot_path', '/tmp/other'), ('environment', {}), ('onnx', {}),
            ('model_recipe_and_compiler_sha256', {}),
            ('agnos', {'image_sha256': '0' * 64}),
            ('device_write_performed', 0),
        ]
        for field, value in changes:
            with self.subTest(field=field):
                altered = copy.deepcopy(plan())
                altered[field] = value
                self.assertIn('frozen native execution plan mismatch', admission.audit(altered, [])['issues'])
        for field, value in [('argv', []), ('cwd', '/tmp/other'),
                             ('stock_scons_target', 'wrong'), ('output', '/tmp/other')]:
            with self.subTest(field=field):
                altered = copy.deepcopy(plan())
                altered['targets'][0][field] = value
                self.assertIn('frozen native execution plan mismatch', admission.audit(altered, [])['issues'])

    def test_fabricated_six_remain_unverified_even_if_byte_verifier_passes(self):
        with patch.object(prep, 'verify_artifact_set', return_value=[]):
            result = admission.audit(plan(), fabricated_records(), Path('/tmp/fabricated'))
        self.assertEqual(result['static_candidates'], 6)
        self.assertEqual(result['decision'], admission.UNVERIFIED)
        self.assertIn(admission.UNVERIFIED, result['issues'])
        self.assertIn(admission.UNAUTHENTICATED, result['issues'])
        self.assertEqual(result['receipt_authentication_status'], 'SELF_REPORTED_NOT_AUTHENTICATED')
        self.assertEqual(result['receipt_field_authentication'], {
            field: 'SELF_REPORTED_NOT_AUTHENTICATED'
            for field in (*admission.REQUIRED_EVIDENCE, 'quality_result')})
        self.assertEqual(result['b3_verified_artifact_count'], 0)
        self.assertFalse(result['b3_completed_6_of_6'])

    def test_cli_fabricated_records_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as temp:
            records = Path(temp) / 'records.json'
            records.write_text(json.dumps(fabricated_records()))
            with patch('sys.argv', ['qcom_b3_admission.py', '--plan', str(admission.PLAN_PATH),
                                    '--records', str(records), '--artifacts', temp]), \
                    patch.object(prep, 'verify_artifact_set', return_value=[]), \
                    redirect_stdout(io.StringIO()) as output:
                self.assertNotEqual(admission.main(), 0)
            self.assertIn(admission.UNVERIFIED, output.getvalue())

    def test_cli_rejects_altered_plan_bytes_before_decode(self):
        with tempfile.TemporaryDirectory() as temp:
            supplied = Path(temp) / 'plan.json'
            supplied.write_bytes(admission.PLAN_PATH.read_bytes() + b' ')
            with patch('sys.argv', ['qcom_b3_admission.py', '--plan', str(supplied)]):
                with self.assertRaises(SystemExit) as error:
                    admission.main()
            self.assertNotEqual(error.exception.code, 0)

    def test_device_node_rejected_without_open(self):
        p = Path('/dev/null')
        if not p.exists():
            self.skipTest('POSIX device node fixture unavailable')
        with patch.object(sys, 'argv', ['qcom_b3_admission.py', '--plan', str(p)]):
            with patch.object(admission.os, 'open', side_effect=AssertionError('opened device node')):
                with self.assertRaises(SystemExit) as err:
                    admission.main()
        self.assertNotEqual(err.exception.code, 0)

    def test_modified_plan_is_rejected_even_if_file_has_same_semantics(self):
        original = admission.PLAN_PATH.read_bytes()
        with tempfile.TemporaryDirectory(prefix='b3c-plan-race-') as d:
            p = Path(d) / 'plan.json'
            p.write_bytes(original + b' ')
            with patch.object(sys, 'argv', ['qcom_b3_admission.py', '--plan', str(p)]):
                with patch.object(admission.model, 'sha256', return_value=admission.PLAN_SHA256):
                    with self.assertRaises(SystemExit) as err:
                        admission.main()
            self.assertNotEqual(err.exception.code, 0)

    def test_oversized_plan_fails_before_byte_read(self):
        with tempfile.TemporaryDirectory(prefix='b3c-plan-oversize-') as d:
            plan_file = Path(d) / 'plan.json'
            plan_file.write_bytes(b'x' * (1024 * 1024 + 1))
            with patch.object(sys, 'argv', ['qcom_b3_admission.py', '--plan', str(plan_file)]):
                with patch.object(Path, 'read_bytes', side_effect=AssertionError('oversized read')):
                    with self.assertRaises(SystemExit) as err:
                        admission.main()
            self.assertNotEqual(err.exception.code, 0)

    def test_bad_records_never_complete(self):
        for records in ([{'artifact': prep.FIRST}],
                        [{'artifact': prep.FIRST}, {'artifact': prep.FIRST}],
                        [{'artifact': 'unknown'}],
                        [{'artifact': ['malformed']}],
                        [{'artifact': prep.FIRST, 'source_commit': '0'*40, 'gpu_backend': 'LLVM'}]):
            result = admission.audit(plan(), records)
            self.assertEqual(result['decision'], admission.UNVERIFIED)
            self.assertEqual(result['b3_verified_artifact_count'], 0)
            self.assertIn(admission.UNVERIFIED, result['issues'])

    def test_evidence_json_rejects_symlink_fifo_oversize_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); record=root/'record.json'; record.write_text('{}')
            link=root/'link.json'; link.symlink_to(record)
            with self.assertRaises(OSError): admission.load_json(link)
            if hasattr(os, 'mkfifo'):
                fifo=root/'fifo.json'; os.mkfifo(fifo)
                with self.assertRaises(ValueError): admission.load_json(fifo)
            record.write_bytes(b'x' * (1024*1024+1))
            with self.assertRaises(ValueError): admission.load_json(record)
            record.write_text('{"x":1,"x":2}')
            with self.assertRaises(ValueError): admission.load_json(record)


if __name__ == '__main__':
    unittest.main()
