import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.release import qcom_b3_prepare as b
from tools.release import mvl_model_artifacts as model


def short_string(value):
    data=value.encode(); return b'\x8c'+bytes([len(data)])+data


def capture(name):
    code=b'\x80\x04'
    for obj in ('_TinyJit','CapturedJit'):
        code+=short_string('tinygrad.engine.jit')+short_string(obj)+b'\x93\x30'
    code+=b'\x5d'
    labels=['metadata','run','input_specs','QCOM']
    if name in model.ARTIFACTS[:2]: labels+=['output_specs','output_slices','input_shapes']
    for label in labels: code+=short_string(label)+b'\x61'
    code+=b'.'
    return len(code).to_bytes(8,'little',signed=True)+code+name.encode()


class B3PrepareTest(unittest.TestCase):
    def records(self, path):
        out=[]
        for name in model.ARTIFACTS:
            data=capture(name);(path/name).write_bytes(data)
            out.append({'artifact':name,'source_commit':b.SOURCE,'tinygrad_commit':b.TINYGRAD,
                'agnos_image_sha256':model.AGNOS199_IMAGE_SHA256,'compiler_exit_code':0,
                'gpu_backend':'QCOM','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
                'peak_rss_bytes':123456,'elapsed_seconds':1.2})
        return out

    def test_six_static_captures_and_negative_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); records=self.records(path)
            self.assertEqual(b.verify_artifact_set(path,records),[])
            records[0]['source_commit']='0'*40
            self.assertTrue(any('provenance mismatch' in x for x in b.verify_artifact_set(path,records)))
            records[0]['source_commit']=b.SOURCE
            records[0]['compiler_exit_code']=1
            self.assertTrue(any('compiler/backend' in x for x in b.verify_artifact_set(path,records)))
            records[0]['compiler_exit_code']=0
            (path/model.ARTIFACTS[0]).write_bytes(b'CPU:LLVM')
            self.assertTrue(any('invalid captured bytes' in x for x in b.verify_artifact_set(path,records)))

    def test_missing_extra_and_duplicate_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); records=self.records(path)
            (path/model.ARTIFACTS[-1]).unlink()
            self.assertTrue(b.verify_artifact_set(path,records))
            records[-1]['sha256']=records[0]['sha256']
            self.assertTrue(any('duplicate output bytes' in x for x in b.validate_capture_records(records)))
            self.assertTrue(any('exact six-artifact' in x for x in b.validate_capture_records(records[:-1])))

    def test_missing_record_resource_and_agnos_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); records=self.records(path)
            records[0]['peak_rss_bytes']=0
            records[1]['agnos_image_sha256']='0'*64
            reasons=b.validate_capture_records(records)
            self.assertTrue(any('resource evidence' in x for x in reasons))
            self.assertTrue(any('provenance mismatch' in x for x in reasons))

    def test_recipe_requires_stock_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            recipe=root/'openpilot/selfdrive/modeld/SConscript';recipe.parent.mkdir(parents=True)
            recipe.write_text('compile_onnx.py compile_warp.py models/dmonitoring_model_tinygrad.pkl models/driving_tinygrad.pkl driving_warp_ dm_warp_ SKIP_TINYGRAD_COMPILE')
            with self.assertRaisesRegex(ValueError,'frozen model recipe missing'):
                b.validate_recipe(root)


if __name__=='__main__': unittest.main()
