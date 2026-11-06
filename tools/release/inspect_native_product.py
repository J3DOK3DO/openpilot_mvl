#!/usr/bin/env python3
"""Read-only ARM64 package inventory; never treats static inspection as device qualification."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

if __package__:
    from tools.release.mvl_model_artifacts import AGNOS_SHA256, ARTIFACTS, MODEL_DIR
else:
    from mvl_model_artifacts import AGNOS_SHA256, ARTIFACTS, MODEL_DIR

MAX_FILES = 20000
MAX_TOTAL_BYTES = 16 * 1024 * 1024 * 1024

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate manifest key {key}')
        result[key] = value
    return result

def elf_identity(path: Path) -> dict:
    completed = subprocess.run(['readelf', '-h', '-l', '-d', '-n', str(path)], text=True, capture_output=True, timeout=15)
    if completed.returncode != 0:
        raise ValueError(f'readelf failed for {path.name}')
    output = completed.stdout
    def field(name):
        match = re.search(rf'^\s*{re.escape(name)}:\s*(.+)$', output, re.MULTILINE)
        return match.group(1).strip() if match else ''
    def bracket(pattern):
        return re.findall(pattern, output)
    return {
        'class': field('Class'), 'machine': field('Machine'), 'os_abi': field('OS/ABI'),
        'interpreter': (bracket(r'\[Requesting program interpreter: ([^\]]+)\]') or [''])[0],
        'needed': bracket(r'\(NEEDED\)\s+Shared library: \[([^\]]+)\]'),
        'runpath': bracket(r'\(RUNPATH\)\s+Library runpath: \[([^\]]+)\]'),
        'rpath': bracket(r'\(RPATH\)\s+Library rpath: \[([^\]]+)\]'),
        'build_id': (bracket(r'Build ID: ([0-9a-fA-F]+)') or [''])[0],
    }

def inspect(source_root: Path, stage: Path, qcom_manifest: Path, expected_source: str) -> dict:
    source_root = source_root.resolve()
    stage = stage.resolve()
    if not re.fullmatch(r'[0-9a-f]{40}', expected_source):
        raise ValueError('expected source must be a full Git SHA')
    if not stage.is_dir() or stage == source_root or stage in source_root.parents or source_root in stage.parents:
        raise ValueError('staging root must be a separate existing directory')
    if stage.as_posix() in ('/data/openpilot', '/data', '/'):
        raise ValueError('refusing installed source or broad filesystem root')
    head = subprocess.check_output(['git', '-C', str(source_root), 'rev-parse', 'HEAD'], text=True).strip()
    if head != expected_source:
        raise ValueError('source checkout differs from expected Git SHA')
    clean = subprocess.check_output(['git', '-c', 'filter.lfs.required=false', '-c', 'filter.lfs.process=', '-c', 'filter.lfs.clean=cat', '-C', str(source_root), 'status', '--porcelain', '--untracked-files=all'], text=True)
    if clean.strip():
        raise ValueError('source checkout is not clean')
    issues = []
    if not qcom_manifest.is_file() or qcom_manifest.is_symlink():
        issues.append('exact-source QCOM manifest absent')
        qcom = None
    else:
        qcom = json.loads(qcom_manifest.read_text(), object_pairs_hook=unique_pairs)
        if qcom.get('source_commit') != expected_source:
            issues.append('QCOM manifest source SHA mismatch')
        if qcom.get('agnos', {}).get('version') != '19.8.1' or qcom.get('agnos', {}).get('image_sha256') != AGNOS_SHA256:
            issues.append('QCOM manifest AGNOS identity mismatch')
        if set(qcom.get('artifacts', {})) != set(ARTIFACTS):
            issues.append('QCOM manifest artifact set incomplete or unexpected')
    rows = []
    total_bytes = 0
    for path in sorted(stage.rglob('*')):
        relative = path.relative_to(stage).as_posix()
        if len(rows) >= MAX_FILES:
            raise ValueError('staging file-count bound exceeded')
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if stat.S_ISLNK(mode):
            target = os.readlink(path)
            if not path.resolve().is_relative_to(stage):
                issues.append(f'escaping symlink: {relative}')
            rows.append({'path': relative, 'kind': 'symlink', 'target': target})
            continue
        if not stat.S_ISREG(mode):
            issues.append(f'unsupported file kind: {relative}')
            continue
        size = path.stat().st_size
        total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError('staging size bound exceeded')
        row = {'path': relative, 'kind': 'file', 'size': size, 'sha256': sha256(path)}
        with path.open('rb') as stream:
            is_elf = stream.read(4) == b'\x7fELF'
        if is_elf:
            row['elf'] = elf_identity(path)
            if row['elf']['class'] != 'ELF64' or 'AArch64' not in row['elf']['machine']:
                issues.append(f'non-AArch64 ELF: {relative}')
            for value in row['elf']['runpath'] + row['elf']['rpath']:
                if any(part.startswith(('/home/', '/tmp/', '/mnt/', '/build/')) for part in value.split(':')):
                    issues.append(f'host-specific ELF library path: {relative}')
        rows.append(row)
    found = {row['path']: row for row in rows if row['kind'] == 'file'}
    for name in ARTIFACTS:
        relative = (MODEL_DIR / name).as_posix()
        row = found.get(relative)
        if row is None:
            issues.append(f'missing stock QCOM output: {relative}')
        elif qcom and qcom.get('artifacts', {}).get(name) != {'sha256': row['sha256'], 'size': row['size']}:
            issues.append(f'QCOM artifact hash/size mismatch: {relative}')
    elf_count = sum('elf' in row for row in rows)
    if elf_count == 0:
        issues.append('no product ELF found')
    return {
        'schema_version': 1,
        'source_commit': head,
        'staging_root': str(stage),
        'qcom_manifest_sha256': sha256(qcom_manifest) if qcom else None,
        'file_count': len(rows), 'total_regular_bytes': total_bytes,
        'elf_count': elf_count, 'files': rows, 'issues': issues,
        'static_decision': 'HOLD_STATIC_ISSUES' if issues else 'STATIC_PARTIAL_INVENTORY_PASS_PRODUCT_SET_UNVERIFIED',
        'device_qualification': 'NOT_TESTED',
        'product_build_claim': 'NOT_ESTABLISHED_BY_THIS_INSPECTOR',
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--staging-root', type=Path, required=True)
    parser.add_argument('--qcom-manifest', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    result = inspect(args.source_root, args.staging_root, args.qcom_manifest, args.expected_source)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(2 if result['issues'] else 0)
