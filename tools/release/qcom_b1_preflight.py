#!/usr/bin/env python3
"""Offline QCOM B1 evidence and capacity checks. No device or build commands."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SOURCE_SHA = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
MANIFEST_SHA = '998b417374930b75338b7ef8be9b3739d3e9e4d130c39ae0aa10e4abfcab9ee4'
TAR_SHA = '37a82b744d079c0a130b3f88e24ba4d56b7aa5db4c0bc709449ed4f0ba3d60fe'
IMAGE_SHA = '80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7'
TINYGRAD_SHA = '92b742f711c7d216fd3ed7a46a30a959e3c43bd4'
RUNNER_SHA = 'sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95'
GRAPH_SHA = '15b18e03bf0aac74df65a723a63538918526b622ceadbe684d038b7997de25fa'
GIB = 1024 ** 3
OUTPUTS = (
    'dmonitoring_model_tinygrad.pkl', 'driving_tinygrad.pkl',
    'driving_warp_1344x760_tinygrad.pkl', 'driving_warp_1928x1208_tinygrad.pkl',
    'dm_warp_1344x760_tinygrad.pkl', 'dm_warp_1928x1208_tinygrad.pkl',
)
FLAGS = 'DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1'
ONNX = {
    'openpilot/selfdrive/modeld/models/dmonitoring_model.onnx': 'dee5a294e8afaacc9295ac5d100e00733ecac278e79264b96331e40a3ede1b04',
    'openpilot/selfdrive/modeld/models/driving_supercombo.onnx': '65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce',
}


def sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'not a regular file: {path}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate key: {key}')
        result[key] = value
    return result


def capacity(available_kib: int, *, source_checkout_gib: float = 1.25,
             archive_extra_gib: float = 0.5, environment_gib: float = 0.5,
             cache_gib: float = 2.0, logs_gib: float = 0.25,
             outputs_scratch_tmp_peak_gib: float | None = None,
             reserve_gib: float = 2.0) -> dict:
    """Scenario arithmetic; unknown peak can never be promoted to GO."""
    values = (source_checkout_gib, archive_extra_gib, environment_gib,
              cache_gib, logs_gib, reserve_gib)
    if not isinstance(available_kib, int) or isinstance(available_kib, bool) or available_kib < 0:
        raise ValueError('available_kib must be a nonnegative integer')
    if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not 0 <= x <= 64 for x in values):
        raise ValueError('invalid capacity allocation')
    if reserve_gib < 2:
        raise ValueError('minimum free-space reserve is 2 GiB')
    if outputs_scratch_tmp_peak_gib is not None and (not isinstance(outputs_scratch_tmp_peak_gib, (int, float)) or
        isinstance(outputs_scratch_tmp_peak_gib, bool) or not 0 <= outputs_scratch_tmp_peak_gib <= 64):
        raise ValueError('invalid peak allocation')
    available_gib = available_kib / (1024 * 1024)
    fixed_gib = sum(values)
    required_gib = None if outputs_scratch_tmp_peak_gib is None else fixed_gib + outputs_scratch_tmp_peak_gib
    return {
        'available_kib': available_kib, 'available_gib': round(available_gib, 6),
        'allocation_gib': dict(zip(('source_checkout', 'archive_extra', 'environment', 'cache', 'logs', 'reserve'), values)),
        'outputs_gpu_scratch_tmp_peak_gib': outputs_scratch_tmp_peak_gib,
        'required_gib': required_gib,
        'arithmetic_fits': None if required_gib is None else available_gib >= required_gib,
        'decision': ('HOLD_REQUIRED_CAPACITY_UNKNOWN' if required_gib is None else
                     'HOLD_LOW_DISK' if available_gib < required_gib else
                     'SCENARIO_FITS_ONLY_PEAK_EVIDENCE_REQUIRED'),
    }


def device_observation(model: str, agnos: str, actual_cpu_mc: int | None,
                       actual_gpu_mc: int | None, virtual_limit_mc: int | None) -> dict:
    holds = []
    if not re.search(r'\bcomma\s*(?:4|four|mici)\b', model.casefold()):
        holds.append('MODEL_MISMATCH')
    if agnos != '19.9':
        holds.append('AGNOS_MISMATCH')
    for name, value in (('CPU', actual_cpu_mc), ('GPU', actual_gpu_mc)):
        if value is None or not isinstance(value, int) or isinstance(value, bool) or value < -20000 or value >= 70000:
            holds.append(f'{name}_ACTUAL_THERMAL_UNKNOWN_OR_HIGH')
    return {'model': model, 'agnos': agnos, 'actual_cpu_mc': actual_cpu_mc,
            'actual_gpu_mc': actual_gpu_mc, 'virtual_limit_mc': virtual_limit_mc,
            'holds': holds, 'decision': 'OBSERVED_IDLE_ONLY' if not holds else 'HOLD_DEVICE_OBSERVATION'}


def git(source: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(source), *args], text=True, stderr=subprocess.PIPE,
                                   env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}).strip()


def audit(source: Path, handoff: Path, graph_log: Path, binary: Path) -> dict:
    manifest_file = handoff / 'manifest.json'
    if sha256(manifest_file) != MANIFEST_SHA or sha256(handoff / 'source.tar') != TAR_SHA:
        raise ValueError('handoff differs from external anchors')
    manifest = json.loads(manifest_file.read_text(), object_pairs_hook=unique_pairs)
    if manifest.get('source_commit') != SOURCE_SHA or manifest.get('source_tar_sha256') != TAR_SHA:
        raise ValueError('handoff source/tar identity mismatch')
    if git(source, 'rev-parse', 'HEAD') != SOURCE_SHA:
        raise ValueError('frozen checkout source mismatch')
    verified = subprocess.run(
        [sys.executable, str(Path(__file__).with_name('preflight_readonly.py')),
         '--repo', str(source), '--commit', SOURCE_SHA],
        text=True, capture_output=True, timeout=180, check=False,
        env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONDONTWRITEBYTECODE': '1'},
    )
    if verified.returncode != 0:
        raise ValueError('frozen source preflight failed')
    source_report = json.loads(verified.stdout, object_pairs_hook=unique_pairs)
    selected = [row for row in source_report.get('lfs_assets', []) if row.get('release_selected')]
    if source_report.get('result') != 'PASS' or source_report.get('issues') or len(selected) != 283 or \
            any(row.get('state') != 'hydrated' for row in selected):
        raise ValueError('frozen source checkout or 283 LFS assets failed preflight')
    links = dict((line.split('\t', 1)[1], line.split()[1]) for line in git(source, 'ls-files', '--stage').splitlines()
                 if line.startswith('160000 '))
    if len(links) != 7 or links != manifest.get('gitlinks') or links.get('tinygrad_repo') != TINYGRAD_SHA:
        raise ValueError('seven pinned gitlinks mismatch')
    if manifest.get('onnx_sha256') != ONNX or tuple(manifest.get('required_qcom_outputs', ())) != OUTPUTS:
        raise ValueError('ONNX or output contract mismatch')
    if any(sha256(source / relative) != digest for relative, digest in ONNX.items()):
        raise ValueError('materialized ONNX bytes mismatch')
    if not manifest.get('no_qcom_outputs_included'):
        raise ValueError('handoff includes QCOM outputs')
    rows = manifest.get('files', [])
    if len(rows) != 4372 or any(not isinstance(row.get('path'), str) or
                                row['path'].startswith('/') or '..' in Path(row['path']).parts for row in rows):
        raise ValueError('handoff path inventory mismatch')
    script = (source / 'openpilot/selfdrive/modeld/SConscript').read_text()
    required = (FLAGS, "if not os.getenv('SKIP_TINYGRAD_COMPILE')", 'compile_onnx.py',
                'compile_warp.py', '--out-of-band --benchmark-runs 1', 'taskset -c 0-7 ',
                'camera_configs = [(c.width, c.height)')
    if any(token not in script for token in required):
        raise ValueError('stock QCOM SConscript recipe changed')
    if (source / 'rootfs').exists():
        raise ValueError('unexpected embedded rootfs')
    graph = graph_log.read_text(errors='replace')
    if sha256(graph_log) != GRAPH_SHA or not graph.rstrip().endswith('scons: done building targets.') or \
            FLAGS not in graph or any(name not in graph for name in OUTPUTS):
        raise ValueError('retained SCons graph identity or six-target recipe mismatch')
    missing = [name for name in OUTPUTS if not (source / 'openpilot/selfdrive/modeld/models' / name).is_file() or
               (source / 'openpilot/selfdrive/modeld/models' / name).is_symlink()]
    with binary.open('rb') as stream:
        elf_header = stream.read(20)
    if elf_header[:5] != b'\x7fELF\x02' or int.from_bytes(elf_header[18:20], 'little') != 183:
        raise ValueError('representative binary is not ELF64 AArch64')
    return {
        'schema_version': 1, 'source_commit': SOURCE_SHA, 'handoff_manifest_sha256': MANIFEST_SHA,
        'handoff_tar_sha256': TAR_SHA, 'handoff_members': len(rows), 'gitlinks': links,
        'onnx_sha256': ONNX, 'required_qcom_outputs': list(OUTPUTS),
        'missing_qcom_outputs': missing, 'stock_qcom_flags': FLAGS,
        'stock_scons_recipe': 'PASS_STATIC_SOURCE_INSPECTION',
        'retained_graph': {'status': 'PASS_DRY_RUN_RETAINED', 'log_sha256': GRAPH_SHA,
                           'six_qcom_targets_in_graph': True, 'not_executed_this_checkpoint': True},
        'representative_library': {'status': 'ELF64_AARCH64_HOST_OBSERVED', 'bytes': binary.stat().st_size,
                                   'sha256': sha256(binary), 'runtime_load': 'NOT_TESTED'},
        'selected_lfs_assets': {'status': 'PASS_FRESH_SOURCE_PREFLIGHT', 'release_selected_hydrated': len(selected)},
        'full_cold_product': 'BLOCKED_SIX_QCOM_OUTPUTS_MISSING',
        'device_qualification': 'NOT_TESTED', 'release_decision': 'PRODUCT_BUILD_INCOMPLETE_HOLD',
        'runner_image_id': RUNNER_SHA, 'agnos199_image_sha256': IMAGE_SHA,
        'limits': ['retained graph does not prove product build', 'runtime load untested',
                   'GPU compilation and peak scratch/RSS unobserved'],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--graph-log', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.source, args.handoff, args.graph_log, args.binary), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
