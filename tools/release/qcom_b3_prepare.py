#!/usr/bin/env python3
"""Exact-source, host-only plan for six QCOM captures. Never starts compilation."""
from __future__ import annotations

import argparse
import math
import hashlib
import json
from pathlib import Path
import re
import subprocess

if __package__:
    from tools.release import mvl_model_artifacts as model
    from tools.release.qcom_b2final import SOURCE, pilot_path
else:
    import mvl_model_artifacts as model
    from qcom_b2final import SOURCE, pilot_path

HANDOFF_MANIFEST_SHA = '998b417374930b75338b7ef8be9b3739d3e9e4d130c39ae0aa10e4abfcab9ee4'
HANDOFF_TAR_SHA = '37a82b744d079c0a130b3f88e24ba4d56b7aa5db4c0bc709449ed4f0ba3d60fe'
TINYGRAD = '92b742f711c7d216fd3ed7a46a30a959e3c43bd4'
FLAGS = 'DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1'
FIRST = 'driving_warp_1344x760_tinygrad.pkl'
TRUSTED_PREFLIGHT = Path(__file__).resolve().with_name('preflight_readonly.py')


def sha(path: Path) -> str:
    return model.sha256(model.regular(path))


def validate_recipe(source: Path) -> dict:
    recipe = source / 'openpilot/selfdrive/modeld/SConscript'
    text = model.regular(recipe).read_text()
    for value in (FLAGS, 'compile_onnx.py', 'compile_warp.py', 'models/dmonitoring_model_tinygrad.pkl',
                  'models/driving_tinygrad.pkl', 'driving_warp_', 'dm_warp_', 'SKIP_TINYGRAD_COMPILE'):
        if value not in text:
            raise ValueError(f'frozen model recipe missing {value}')
    return {p: sha(source/p) for p in ('openpilot/selfdrive/modeld/SConscript',
            'tinygrad_repo/examples/openpilot/compile_onnx.py',
            'tinygrad_repo/examples/openpilot/compile_warp.py')}


def prepare(source: Path, handoff: Path, image: Path, rootfs: Path, component_manifest: Path,
            run_id: str) -> dict:
    source = source.resolve()
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != SOURCE:
        raise ValueError('wrong frozen product commit')
    preflight = subprocess.run(['python3', str(TRUSTED_PREFLIGHT),
        '--repo', str(source), '--commit', SOURCE], capture_output=True, text=True, timeout=120)
    if preflight.returncode or json.loads(preflight.stdout).get('result') != 'PASS':
        raise ValueError('exact-source preflight failed')
    if model.git(source/'tinygrad_repo', 'rev-parse', 'HEAD') != TINYGRAD:
        raise ValueError('wrong tinygrad compiler gitlink')
    if sha(handoff/'manifest.json') != HANDOFF_MANIFEST_SHA or sha(handoff/'source.tar') != HANDOFF_TAR_SHA:
        raise ValueError('trusted handoff hash mismatch')
    agnos = model.agnos_identity(image, rootfs, '19.9', component_manifest)
    files = validate_recipe(source)
    onnx = {name: {'sha256': sha(source/model.MODEL_DIR/name),
                   'bytes': (source/model.MODEL_DIR/name).stat().st_size} for name in model.ONNX}
    if any((source/model.MODEL_DIR/name).exists() for name in model.ARTIFACTS):
        raise ValueError('pre-existing model artifact would contaminate clean compilation')
    pilot = pilot_path(run_id)
    targets = []
    for index, name in enumerate((FIRST,) + tuple(x for x in model.ARTIFACTS if x != FIRST)):
        target = 'openpilot/selfdrive/modeld/models/' + name
        targets.append({'order': index+1, 'artifact': name, 'stock_scons_target': target,
            'argv': ['/usr/local/venv/bin/python3', '-m', 'SCons', '-j1', '--minimal',
                     'cache_dir=' + str(pilot/'cache'), target],
            'cwd': str(pilot/'source'), 'output': str(pilot/'source'/target),
            'compiler_exit': 'NOT_EXECUTED', 'output_sha256': None, 'runtime_inference': 'NOT_TESTED'})
    return {'schema_version': 1, 'decision': 'OFFLINE_PLAN_ONLY_NO_DEVICE_GO', 'source_commit': SOURCE,
        'tinygrad_commit': TINYGRAD, 'agnos': agnos,
        'handoff_manifest_sha256': HANDOFF_MANIFEST_SHA, 'handoff_tar_sha256': HANDOFF_TAR_SHA,
        'model_recipe_and_compiler_sha256': files, 'onnx': onnx,
        'qcom_flags': FLAGS, 'unset_environment': ['SKIP_TINYGRAD_COMPILE'],
        'pilot_path': str(pilot), 'environment': {'PATH':'/usr/local/venv/bin:/usr/bin:/bin',
        'TMPDIR':str(pilot/'tmp'), 'HOME':str(pilot/'home'), 'PYTHONDONTWRITEBYTECODE':'1'},
        'targets': targets, 'device_write_performed': False,
        'required_before_execution': ['separate device transfer/compilation authorization',
        'verified aggregate hard quota and free-space reserve', 'independent authenticated live parked-state monitor',
        'actual CPU/GPU thermal and GPU error monitoring', 'device-tested memory ceiling and abort/recovery']}


def validate_capture_records(records: list[dict]) -> list[str]:
    issues = []
    if len(records) != len(model.ARTIFACTS) or {x.get('artifact') for x in records} != set(model.ARTIFACTS):
        issues.append('exact six-artifact set required')
    hashes = set()
    for record in records:
        name = record.get('artifact')
        if name not in model.ARTIFACTS:
            continue
        if record.get('source_commit') != SOURCE or record.get('tinygrad_commit') != TINYGRAD or \
                record.get('agnos_image_sha256') != model.AGNOS199_IMAGE_SHA256:
            issues.append(f'{name}: provenance mismatch')
        if type(record.get('compiler_exit_code')) is not int or record['compiler_exit_code'] != 0 or record.get('gpu_backend') != 'QCOM':
            issues.append(f'{name}: compiler/backend unverified')
        digest = record.get('sha256')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or \
                not isinstance(record.get('bytes'), int) or isinstance(record['bytes'], bool) or record['bytes'] <= 0:
            issues.append(f'{name}: missing output identity')
        elif digest in hashes:
            issues.append(f'{name}: duplicate output bytes')
        else:
            hashes.add(digest)
        elapsed = record.get('elapsed_seconds')
        if not isinstance(record.get('peak_rss_bytes'), int) or isinstance(record['peak_rss_bytes'], bool) or record['peak_rss_bytes'] <= 0 or \
                not isinstance(elapsed, (int,float)) or isinstance(elapsed, bool) or not math.isfinite(elapsed) or elapsed <= 0:
            issues.append(f'{name}: resource evidence missing')
    return issues


def verify_artifact_set(directory: Path, records: list[dict]) -> list[str]:
    """Static byte inspection only; compiler exit and inference need independent proof."""
    issues = validate_capture_records(records)
    by_name = {r.get('artifact'): r for r in records}
    if not directory.is_dir() or directory.is_symlink():
        return issues + ['artifact directory missing or symlink']
    if {p.name for p in directory.iterdir()} != set(model.ARTIFACTS):
        issues.append('artifact directory contains missing or extra files')
    for name in model.ARTIFACTS:
        try:
            identity = model.qcom_capture(directory / name)
        except (OSError, ValueError) as exc:
            issues.append(f'{name}: invalid captured bytes: {exc}')
            continue
        record = by_name.get(name)
        if not record or record.get('sha256') != identity['sha256'] or record.get('bytes') != identity['size']:
            issues.append(f'{name}: record differs from actual bytes')
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--agnos-image', type=Path, required=True)
    parser.add_argument('--agnos-rootfs', type=Path, required=True)
    parser.add_argument('--agnos-component-manifest', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source,args.handoff,args.agnos_image,args.agnos_rootfs,
                             args.agnos_component_manifest,args.run_id), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__': raise SystemExit(main())
