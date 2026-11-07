#!/usr/bin/env python3
"""Host-only AGNOS 19.9 full-product preflight and non-installable package contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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


def preflight(source: Path, artifacts: Path, onnx_assets: Path, image: Path,
              rootfs: Path, component_manifest: Path, build_root: Path) -> dict:
    if source_head(source) != SOURCE:
        raise ValueError('frozen product source mismatch')
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


def package_manifest(source: Path, stage: Path, qcom_manifest: Path, *, test_record_sha256: str,
                     independent_review_sha256: str) -> dict:
    if source_head(source) != SOURCE:
        raise ValueError('product source mismatch')
    report = inspector.inspect(source, stage, qcom_manifest, SOURCE, '19.9')
    if report['issues']:
        raise ValueError('product stage has static issues: '+', '.join(report['issues'][:3]))
    for value in (test_record_sha256, independent_review_sha256):
        if len(value) != 64 or any(x not in '0123456789abcdef' for x in value):
            raise ValueError('invalid external evidence SHA-256')
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
