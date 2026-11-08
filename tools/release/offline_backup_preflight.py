#!/usr/bin/env python3
"""Verify an offline known-good backup inventory; never authorizes installation."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

KNOWN_GOOD = 'a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1'
DECISION = 'NOT_INSTALLABLE'
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _safe_path(name: object) -> PurePosixPath:
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('invalid backup path')
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('unsafe backup path')
    if path.parts[0] not in ('known_good', 'owner_data'):
        raise ValueError('unrecognized backup category')
    if any(part.casefold() == 'params' for part in path.parts) or path.name in ('panda.bin', 'panda.signed'):
        raise ValueError('protected data is outside this backup contract')
    return path


def verify(root: Path, manifest: dict[str, object]) -> dict[str, object]:
    """Check bytes against an externally retained manifest in an isolated host copy.

    The manifest itself still needs an independent trusted hash. This verifier
    checks completeness of the listed local files, not device or release state.
    """
    if type(manifest) is not dict or set(manifest) != {'schema_version', 'known_good_commit', 'files'}:
        raise ValueError('invalid backup manifest schema')
    if manifest['schema_version'] != 1 or manifest['known_good_commit'] != KNOWN_GOOD:
        raise ValueError('known-good identity mismatch')
    entries = manifest['files']
    if type(entries) is not list or not entries:
        raise ValueError('backup inventory is empty or invalid')
    if root.is_symlink() or not root.is_dir():
        raise ValueError('backup root is not a directory')
    seen: set[str] = set()
    if not any(type(entry) is dict and isinstance(entry.get('path'), str) and
               entry['path'].startswith('known_good/') for entry in entries):
        raise ValueError('known-good backup entry missing')
    for entry in entries:
        if type(entry) is not dict or set(entry) != {'path', 'sha256', 'size'}:
            raise ValueError('invalid backup file entry')
        rel = _safe_path(entry['path'])
        name = rel.as_posix()
        if name in seen:
            raise ValueError('duplicate backup path')
        seen.add(name)
        if type(entry['size']) is not int or entry['size'] < 0 or not isinstance(entry['sha256'], str) or not _SHA.fullmatch(entry['sha256']):
            raise ValueError('invalid backup size or digest')
        candidate = root
        for part in rel.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError('backup symlink rejected')
        if not candidate.is_file():
            raise ValueError('backup file missing')
        digest = hashlib.sha256()
        size = 0
        with candidate.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
                size += len(block)
        if size != entry['size'] or digest.hexdigest() != entry['sha256']:
            raise ValueError('backup file integrity mismatch')
    actual = {p.relative_to(root).as_posix() for category in ('known_good', 'owner_data')
              for p in (root / category).rglob('*') if p.is_file() or p.is_symlink()}
    if actual != seen:
        raise ValueError('backup inventory incomplete or contains extras')
    return {'decision': DECISION, 'install_allowed': False, 'backup_inventory': 'HOST_COPY_BYTES_MATCH',
            'known_good_currently_installed_verified': False, 'file_count': len(seen),
            'manifest_trust': 'EXTERNAL_HASH_REQUIRED', 'device_write_performed': False}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        if not _SHA.fullmatch(args.expected_manifest_sha256):
            raise ValueError('invalid expected manifest digest')
        raw = args.manifest.read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.expected_manifest_sha256:
            raise ValueError('backup manifest digest mismatch')
        report = verify(args.root, json.loads(raw))
    except (OSError, ValueError) as error:
        report = {'decision': DECISION, 'install_allowed': False, 'input_error': str(error)}
    print(json.dumps(report, sort_keys=True))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
