import copy
import unittest

from tools.release import mvl_model_artifacts as model
from tools.release import qcom_b3_admission as admission
from tools.release import qcom_b3_prepare as prep


def plan():
    names = [prep.FIRST] + [name for name in model.ARTIFACTS if name != prep.FIRST]
    return {'source_commit': prep.SOURCE, 'tinygrad_commit': prep.TINYGRAD,
            'agnos': {'image_sha256': model.AGNOS199_IMAGE_SHA256,
                      'component_manifest_sha256': model.AGNOS199_MANIFEST_SHA256},
            'handoff_manifest_sha256': prep.HANDOFF_MANIFEST_SHA,
            'handoff_tar_sha256': prep.HANDOFF_TAR_SHA,
            'targets': [{'artifact': name, 'stock_scons_target': str(model.MODEL_DIR/name)} for name in names]}


class AdmissionTest(unittest.TestCase):
    def test_prepared_is_not_safety_approval(self):
        result = admission.audit(plan(), [])
        self.assertEqual(result['decision'], 'PREPARED_NO_QCOM_DEVICE')
        self.assertEqual(result['b3_verified_artifact_count'], 0)
        self.assertEqual(result['b2_safety_status'], 'NOT_SAFETY_ACCEPTED_NOT_PASSED')
        self.assertFalse(result['g10_promotion'])

    def test_stale_plan_rejected(self):
        for path, value in (('source_commit', '0'*40), ('tinygrad_commit', '0'*40),
                            ('handoff_manifest_sha256', '0'*64)):
            altered = copy.deepcopy(plan())
            altered[path] = value
            self.assertIn('plan provenance mismatch', admission.audit(altered, [])['issues'])
        altered = plan()
        altered['targets'][0]['stock_scons_target'] = 'wrong'
        self.assertIn('plan target sequence mismatch', admission.audit(altered, [])['issues'])

    def test_bad_records_never_complete(self):
        for records in ([{'artifact': prep.FIRST}],
                        [{'artifact': prep.FIRST}, {'artifact': prep.FIRST}],
                        [{'artifact': 'unknown'}],
                        [{'artifact': ['malformed']}],
                        [{'artifact': prep.FIRST, 'source_commit': '0'*40, 'gpu_backend': 'LLVM'}]):
            result = admission.audit(plan(), records)
            self.assertEqual(result['decision'], 'PREPARED_NO_QCOM_DEVICE')
            self.assertEqual(result['b3_verified_artifact_count'], 0)
            self.assertTrue(result['issues'])


if __name__ == '__main__':
    unittest.main()
