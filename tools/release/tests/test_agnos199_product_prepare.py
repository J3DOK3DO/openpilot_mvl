import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools.release import agnos199_product_prepare as g
from tools.release import mvl_model_artifacts as model

class ProductPrepareTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.source=self.base/'source';self.source.mkdir()
        self.artifacts=self.base/'artifacts';self.artifacts.mkdir()
        self.stage=self.base/'stage'
        self.agnos={'version':'19.9','image_sha256':model.AGNOS199_IMAGE_SHA256,
                    'component_manifest_sha256':model.AGNOS199_MANIFEST_SHA256}

    def call(self):
        return g.preflight(self.source,self.artifacts,self.base/'onnx',self.base/'image',
                           self.base/'root',self.base/'agnos.json',self.stage)

    def test_missing_six_outputs_holds_and_never_runs(self):
        with patch.object(g,'verify_source'),patch.object(model,'agnos_identity',return_value=self.agnos):
            result=self.call()
        self.assertEqual(result['decision'],'HOLD_QCOM_ARTIFACTS_MISSING_OR_EXTRA')
        self.assertEqual(set(result['missing']),set(model.ARTIFACTS))
        self.assertFalse(result['device_write_performed'])
        self.assertFalse(self.stage.exists())

    def test_complete_static_inputs_only_prepare_build_command(self):
        for name in model.ARTIFACTS:(self.artifacts/name).write_bytes(b'fixture')
        with patch.object(g,'verify_source'),patch.object(model,'agnos_identity',return_value=self.agnos),\
             patch.object(model,'inventory',return_value={'artifacts':{}}):
            result=self.call()
        self.assertEqual(result['decision'],'STATIC_INPUTS_VERIFIED_BUILD_NOT_EXECUTED')
        self.assertEqual(result['actual_build_exit'],'NOT_EXECUTED')
        self.assertEqual(result['build_cwd'],str(self.stage/'source'))
        self.assertIn('SKIP_TINYGRAD_COMPILE',result['unset_environment'])
        self.assertFalse(self.stage.exists())

    def test_wrong_commit_and_unsafe_destination_rejected(self):
        with patch.object(g,'source_head',return_value='0'*40):
            with self.assertRaisesRegex(ValueError,'source mismatch'):self.call()
        with patch.object(g,'verify_source'):
            with self.assertRaisesRegex(ValueError,'isolated host storage'):
                g.preflight(self.source,self.artifacts,self.base/'onnx',self.base/'image',
                    self.base/'root',self.base/'agnos.json',Path('/data/openpilot'))

    def test_execute_cli_stays_disabled(self):
        command=[sys.executable,'tools/release/agnos199_product_prepare.py','--execute',
            '--source','/tmp/source','--artifacts','/tmp/none','--onnx-assets','/tmp/none',
            '--agnos-image','/tmp/none','--agnos-rootfs','/tmp/none',
            '--agnos-component-manifest','/tmp/none','--build-root','/tmp/stage']
        run=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)['decision'],'NO_GO_EXECUTION_DISABLED_CAMPAIGN1')

    def test_manifest_never_claims_installable(self):
        report={'issues':[],'qcom_manifest_sha256':'a'*64,'files':[{'path':'binary','sha256':'b'*64}], 'elf_count':1}
        def git_output(argv,**kwargs):
            if argv[3]=='ls-tree': return '160000 commit '+('c'*40)+'\t'+argv[-1]+'\n'
            raise AssertionError(argv)
        commit='a'*40
        test=self.base/'tests.json';test.write_text(json.dumps({'tested_commit':commit,'product_source_commit':g.SOURCE,
            'passed':92,'failed':0}))
        review=self.base/'review.json';review.write_text(json.dumps({'tested_commit':commit,
            'product_source_commit':g.SOURCE,'verdict':'PASS_OFFLINE_SCOPE'}))
        with patch.object(g,'verify_source'),patch.object(g.inspector,'inspect',return_value=report),\
             patch.object(g.subprocess,'check_output',side_effect=git_output):
            manifest=g.package_manifest(self.source,self.stage,self.base/'qcom.json',
                test_record=test,independent_review=review,expected_engineering_commit=commit)
        self.assertEqual(manifest['classification'],'NOT_INSTALLABLE_TARGET_RUNTIME_PENDING')
        self.assertEqual(len(manifest['submodule_gitlinks']),7)
        self.assertEqual(manifest['physical_c4'],'NOT_TESTED')
        self.assertEqual(manifest['engineering_tested_commit'],commit)

    def test_dirty_source_preflight_and_unbound_evidence_rejected(self):
        self.assertTrue(g.TRUSTED_PREFLIGHT.is_file())
        probe=subprocess.run([sys.executable,str(g.TRUSTED_PREFLIGHT),'--help'],capture_output=True,text=True)
        self.assertEqual(probe.returncode,0,probe.stderr)
        with patch.object(g,'source_head',return_value=g.SOURCE),patch.object(g.subprocess,'run') as run:
            run.return_value.returncode=1
            run.return_value.stdout=json.dumps({'result':'HOLD','dirty_paths':['SConstruct']})
            with self.assertRaisesRegex(ValueError,'preflight failed'):
                g.verify_source(self.source)
            self.assertEqual(Path(run.call_args.args[0][1]),g.TRUSTED_PREFLIGHT)
            self.assertNotEqual(Path(run.call_args.args[0][1]),self.source/'tools/release/preflight_readonly.py')
        record=self.base/'test.json'
        record.write_text(json.dumps({'tested_commit':'b'*40,'product_source_commit':g.SOURCE,
                                      'passed':92,'failed':0}))
        with self.assertRaisesRegex(ValueError,'binding mismatch'):
            g.verified_record(record,'a'*40,'test')

if __name__=='__main__':unittest.main()
