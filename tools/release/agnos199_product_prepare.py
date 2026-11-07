#!/usr/bin/env python3
"""Host-only AGNOS 19.9 full-product preflight and non-installable package contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

if __package__:
    from tools.release import mvl_model_artifacts as model
    from tools.release import inspect_native_product as inspector
    from tools.release.qcom_b2final import SOURCE
else:
    import mvl_model_artifacts as model
    import inspect_native_product as inspector
    from qcom_b2final import SOURCE

KNOWN_GOOD = 'a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1'


def source_head(source: Path) -> str:
    return subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'], text=True).strip()


def verify_source(source: Path) -> None:
    if source_head(source) != SOURCE:
        raise ValueError('frozen product source mismatch')
    check = subprocess.run(['python3', str(source/'tools/release/preflight_readonly.py'),
        '--repo', str(source), '--commit', SOURCE], capture_output=True, text=True, timeout=120)
    try:
        result = json.loads(check.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError('source preflight did not return valid evidence') from exc
    if check.returncode or result.get('result') != 'PASS' or result.get('dirty_paths'):
        raise ValueError('frozen source content or worktree preflight failed')


def verified_record(path: Path, expected_engineering_commit: str, kind: str) -> tuple[dict,str]:
    if not re.fullmatch('[0-9a-f]{40}', expected_engineering_commit):
        raise ValueError('invalid expected engineering commit')
    model.regular(path)
    if path.stat().st_size > 1024*1024:
        raise ValueError('oversized evidence record')
    data = path.read_bytes()
    record = json.loads(data, object_pairs_hook=model.no_duplicate_keys)
    if record.get('tested_commit') != expected_engineering_commit or record.get('product_source_commit') != SOURCE:
        raise ValueError(f'{kind} commit/source binding mismatch')
    if kind == 'test' and (record.get('failed') != 0 or record.get('passed', 0) <= 0):
        raise ValueError('test record is not passing')
    if kind == 'review' and record.get('verdict') != 'PASS_OFFLINE_SCOPE':
        raise ValueError('independent review record is not passing')
    return record, hashlib.sha256(data).hexdigest()


def preflight(source: Path, artifacts: Path, onnx_assets: Path, image: Path,
              rootfs: Path, component_manifest: Path, build_root: Path) -> dict:
    verify_source(source)
    resolved_build = build_root.resolve(strict=False)
    resolved_source = source.resolve(strict=True)
    if not build_root.is_absolute() or '..' in build_root.parts or resolved_build == resolved_source or \
            resolved_build.is_relative_to(resolved_source) or resolved_build.is_relative_to(Path('/data')) or \
            not (resolved_build.is_relative_to(Path('/tmp')) or resolved_build.is_relative_to(Path('/mnt/commadrive'))):
        raise ValueError('build root must be isolated host storage')
    agnos = model.agnos_identity(image, rootfs, '19.9', component_manifest)
    try:
        actual = {p.name for p in artifacts.iterdir()} if artifacts.is_dir() and not artifacts.is_symlink() else set()
    except OSError:
        actual = set()
    missing = sorted(set(model.ARTIFACTS)-actual)
    if missing or actual != set(model.ARTIFACTS):
        return {'decision':'HOLD_QCOM_ARTIFACTS_MISSING_OR_EXTRA','missing':missing,
                'unexpected':sorted(actual-set(model.ARTIFACTS)),'source_commit':SOURCE,'agnos':agnos,
                'device_write_performed':False}
    package = model.inventory(source, onnx_assets, artifacts, image, rootfs, '19.9', component_manifest)
    return {'decision':'STATIC_INPUTS_VERIFIED_BUILD_NOT_EXECUTED','source_commit':SOURCE,
            'agnos':agnos,'qcom_input_manifest':package,
            'build_command':['/usr/local/venv/bin/python3','-m','SCons','-j1','--minimal',
                             'cache_dir='+str(build_root/'cache')],
            'build_cwd':str(build_root/'source'),'environment':{'PATH':'/usr/local/venv/bin:/usr/bin:/bin',
            'TMPDIR':str(build_root/'tmp'),'HOME':str(build_root/'home'),
            'PYTHONDONTWRITEBYTECODE':'1'},'unset_environment':['SKIP_TINYGRAD_COMPILE'],
            'actual_build_exit':'NOT_EXECUTED','device_write_performed':False}


def package_manifest(source: Path, stage: Path, qcom_manifest: Path, *, test_record: Path,
                     independent_review: Path, expected_engineering_commit: str) -> dict:
    verify_source(source)
    report = inspector.inspect(source, stage, qcom_manifest, SOURCE, '19.9')
    if report['issues']:
        raise ValueError('product stage has static issues: '+', '.join(report['issues'][:3]))
    _, test_record_sha256 = verified_record(test_record, expected_engineering_commit, 'test')
    _, independent_review_sha256 = verified_record(independent_review, expected_engineering_commit, 'review')
    links = {}
    for path in ('msgq_repo','opendbc_repo','openpilot/sunnypilot/neural_network_data',
                 'panda','rednose_repo','teleoprtc_repo','tinygrad_repo'):
        entry = subprocess.check_output(['git','-C',str(source),'ls-tree','HEAD',path],text=True).strip().split()
        if len(entry) < 3 or entry[0:2] != ['160000','commit']:
            raise ValueError('missing pinned submodule gitlink: '+path)
        links[path]=entry[2]
    return {'schema_version':1,'classification':'NOT_INSTALLABLE_TARGET_RUNTIME_PENDING',
        'source_commit':SOURCE,'submodule_gitlinks':links,'tinygrad_commit':links['tinygrad_repo'],
        'agnos_version':'19.9','agnos_raw_image_sha256':model.AGNOS199_IMAGE_SHA256,
        'agnos_component_manifest_sha256':model.AGNOS199_MANIFEST_SHA256,
        'known_good_installed_commit':KNOWN_GOOD,'qcom_manifest_sha256':report['qcom_manifest_sha256'],
        'engineering_tested_commit':expected_engineering_commit,
        'test_record_sha256':test_record_sha256,'independent_review_sha256':independent_review_sha256,
        'stage_files':report['files'],'stage_elf_count':report['elf_count'],
        'target_runtime':'NOT_TESTED','physical_c4':'NOT_TESTED','device_write_performed':False}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--onnx-assets',type=Path,required=True)
    parser.add_argument('--agnos-image',type=Path,required=True)
    parser.add_argument('--agnos-rootfs',type=Path,required=True)
    parser.add_argument('--agnos-component-manifest',type=Path,required=True)
    parser.add_argument('--build-root',type=Path,required=True)
    args=parser.parse_args()
    if args.execute:
        print(json.dumps({'decision':'NO_GO_EXECUTION_DISABLED_CAMPAIGN1','device_write_performed':False}))
        return 2
    print(json.dumps(preflight(args.source,args.artifacts,args.onnx_assets,args.agnos_image,
        args.agnos_rootfs,args.agnos_component_manifest,args.build_root),indent=2,sort_keys=True))
    return 0


if __name__=='__main__': raise SystemExit(main())
