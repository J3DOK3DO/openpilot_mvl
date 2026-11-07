#!/usr/bin/env python3
"""Static AGNOS 19.9 ABI inspection; direct dependencies only, no runtime claim."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

if __package__:
    from tools.release.inspect_native_product import elf_identity
else:
    from inspect_native_product import elf_identity

SEARCH = ('usr/lib/aarch64-linux-gnu', 'lib/aarch64-linux-gnu',
          'usr/local/lib', 'usr/local/venv/lib')


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def version_needs(output: str) -> dict[str, list[str]]:
    section = output.split('Version needs section', 1)
    if len(section) != 2:
        return {}
    result: dict[str, set[str]] = {}
    current = None
    for line in section[1].splitlines():
        match = re.search(r'\bFile: ([^\s]+)', line)
        if match:
            current = match.group(1)
            result.setdefault(current, set())
        match = re.search(r'\bName: ((?:GLIBC|GLIBCXX|CXXABI)_[A-Za-z0-9_.]+)', line)
        if match and current:
            result[current].add(match.group(1))
    return {name: sorted(values) for name, values in result.items()}


def provided_versions(path: Path) -> set[str]:
    result = subprocess.run(['readelf', '-V', str(path)], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise ValueError(f'readelf version inspection failed: {path.name}')
    definitions = result.stdout.split('Version definition section', 1)
    if len(definitions) != 2:
        return set()
    section = definitions[1].split('Version needs section', 1)[0]
    return set(re.findall(r'\bName: ((?:GLIBC|GLIBCXX|CXXABI)_[A-Za-z0-9_.]+)', section))


def resolve_needed(rootfs: Path, name: str) -> Path | None:
    if not re.fullmatch(r'[A-Za-z0-9_.+\-]+\.so(?:\.[0-9]+)*', name):
        raise ValueError('invalid shared library name')
    base = rootfs.resolve(strict=True)
    for directory in SEARCH:
        candidate = base / directory / name
        if candidate.is_file():
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(base):
                raise ValueError('dependency symlink escapes AGNOS rootfs')
            return resolved
    return None


def inspect(binary: Path, rootfs: Path, expected_sha256: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256) or binary.is_symlink() or not binary.is_file():
        raise ValueError('invalid binary identity')
    if digest(binary) != expected_sha256:
        raise ValueError('binary hash mismatch')
    root = rootfs.resolve(strict=True)
    identity = elf_identity(binary)
    issues = []
    if identity['class'] != 'ELF64' or 'AArch64' not in identity['machine']:
        issues.append('not an ELF64 AArch64 binary')
    versions = subprocess.run(['readelf', '-V', str(binary)], capture_output=True, text=True, timeout=20)
    if versions.returncode:
        raise ValueError('binary version inspection failed')
    needs = version_needs(versions.stdout)
    dependencies = []
    for name in identity['needed']:
        path = resolve_needed(root, name)
        if path is None:
            issues.append(f'direct dependency absent in AGNOS rootfs: {name}')
            dependencies.append({'name':name, 'path':None, 'sha256':None, 'missing_versions':needs.get(name, [])})
            continue
        supplied = provided_versions(path)
        missing = sorted(set(needs.get(name, [])) - supplied)
        if missing:
            issues.append(f'direct dependency lacks required versions: {name}: {missing}')
        dependencies.append({'name':name, 'path':str(path.relative_to(root)),
                             'sha256':digest(path), 'required_versions':needs.get(name, []),
                             'missing_versions':missing})
    for value in identity['runpath'] + identity['rpath']:
        for part in value.split(':'):
            if part.startswith(('/tmp/', '/home/', '/mnt/', '/build/')):
                issues.append('host-specific RUNPATH/RPATH')
            elif part.startswith('/') and not (root/part.lstrip('/')).is_dir():
                issues.append(f'RUNPATH/RPATH directory absent in AGNOS rootfs: {part}')
    return {'schema_version':1, 'classification':'REPRESENTATIVE_STATIC_ABI_ONLY',
            'binary_sha256':expected_sha256, 'elf':identity,
            'version_needs':needs, 'direct_dependencies':dependencies,
            'issues':issues, 'static_decision':'HOLD_STATIC_ABI_ISSUES' if issues else 'PASS_REPRESENTATIVE_STATIC_ABI',
            'transitive_dependencies':'NOT_CHECKED', 'agnos_runtime_load':'NOT_TESTED',
            'complete_product':'NOT_BUILT', 'device_qualification':'NOT_TESTED'}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--rootfs',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    args=parser.parse_args()
    report=inspect(args.binary,args.rootfs,args.sha256)
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if not report['issues'] else 2


if __name__=='__main__':raise SystemExit(main())
