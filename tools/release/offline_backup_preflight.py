#!/usr/bin/env python3
"""Verify an offline known-good backup inventory; never authorizes installation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

KNOWN_GOOD = 'a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1'
DECISION = 'NOT_INSTALLABLE'
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_MAX_MANIFEST_BYTES = 1024 * 1024
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK


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
    expected: dict[str, dict[str, object]] = {}
    if not any(type(entry) is dict and isinstance(entry.get('path'), str) and
               entry['path'].startswith('known_good/') for entry in entries):
        raise ValueError('known-good backup entry missing')
    for entry in entries:
        if type(entry) is not dict or set(entry) != {'path', 'sha256', 'size'}:
            raise ValueError('invalid backup file entry')
        rel = _safe_path(entry['path'])
        name = rel.as_posix()
        if name in expected:
            raise ValueError('duplicate backup path')
        if type(entry['size']) is not int or entry['size'] < 0 or not isinstance(entry['sha256'], str) or not _SHA.fullmatch(entry['sha256']):
            raise ValueError('invalid backup size or digest')
        expected[name] = entry
    actual: set[str] = set()
    # root's parent is a trusted isolated host directory. All descendants are
    # opened relative to held directory fds, so path replacement cannot redirect
    # a read outside this tree. A concurrent in-place writer still requires an
    # immutable snapshot or external isolation for stronger assurance.
    try:
        root_fd = os.open(root, _DIR_FLAGS)
    except OSError as exc:
        raise ValueError('backup root is not a trusted directory') from exc
    try:
        for category in ('known_good', 'owner_data'):
            try:
                category_fd = os.open(category, _DIR_FLAGS, dir_fd=root_fd)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ValueError('backup category is unsafe') from exc
            try:
                _scan_directory(category_fd, category, expected, actual)
            finally:
                os.close(category_fd)
    finally:
        os.close(root_fd)
    if actual != set(expected):
        raise ValueError('backup inventory incomplete or contains extras')
    return {'decision': DECISION, 'install_allowed': False, 'backup_inventory': 'HOST_COPY_BYTES_MATCH',
            'known_good_currently_installed_verified': False, 'file_count': len(actual),
            'manifest_trust': 'EXTERNAL_HASH_REQUIRED', 'device_write_performed': False}


def _scan_directory(directory_fd: int, prefix: str, expected: dict[str, dict[str, object]],
                    actual: set[str]) -> None:
    before = os.fstat(directory_fd)
    for name in os.listdir(directory_fd):
        path = f'{prefix}/{name}'
        try:
            entry_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISDIR(entry_stat.st_mode):
                if not any(item.startswith(path + '/') for item in expected):
                    raise ValueError('backup inventory incomplete or contains extras')
                child_fd = os.open(name, _DIR_FLAGS, dir_fd=directory_fd)
                try:
                    child = os.fstat(child_fd)
                    if (entry_stat.st_dev, entry_stat.st_ino) != (child.st_dev, child.st_ino):
                        raise ValueError('backup directory changed during verification')
                    _scan_directory(child_fd, path, expected, actual)
                    linked = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if (linked.st_dev, linked.st_ino) != (child.st_dev, child.st_ino):
                        raise ValueError('backup directory changed during verification')
                finally:
                    os.close(child_fd)
                continue
            if not stat.S_ISREG(entry_stat.st_mode):
                raise ValueError('backup special file or hardlink rejected')
            # O_NONBLOCK prevents a swapped-in FIFO from hanging the verifier.
            leaf_fd = os.open(name, _FILE_FLAGS, dir_fd=directory_fd)
        except OSError as exc:
            raise ValueError('backup entry changed or is unsafe') from exc
        try:
            first = os.fstat(leaf_fd)
            if (entry_stat.st_dev, entry_stat.st_ino) != (first.st_dev, first.st_ino):
                raise ValueError('backup file changed during verification')
            if not stat.S_ISREG(first.st_mode) or first.st_nlink != 1:
                raise ValueError('backup special file or hardlink rejected')
            if path not in expected:
                raise ValueError('backup inventory incomplete or contains extras')
            digest = hashlib.sha256()
            size = 0
            while block := os.read(leaf_fd, 1024 * 1024):
                digest.update(block)
                size += len(block)
            last = os.fstat(leaf_fd)
            if ((first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns, first.st_ctime_ns) !=
                (last.st_dev, last.st_ino, last.st_size, last.st_mtime_ns, last.st_ctime_ns)):
                raise ValueError('backup file changed during verification')
            target = expected[path]
            if size != target['size'] or digest.hexdigest() != target['sha256']:
                raise ValueError('backup file integrity mismatch')
            actual.add(path)
        finally:
            os.close(leaf_fd)
    after = os.fstat(directory_fd)
    if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('backup directory changed during verification')


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate backup manifest key')
        result[key] = value
    return result


def _manifest_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _read_manifest(path: Path) -> bytes:
    """Bound a regular manifest read through a non-following held descriptor."""
    required = ('O_NOFOLLOW', 'O_NONBLOCK', 'O_CLOEXEC')
    if any(not isinstance(getattr(os, name, None), int) for name in required):
        raise ValueError('safe manifest opening is unavailable on this platform')
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('backup manifest is not a regular file')
    if before.st_size > _MAX_MANIFEST_BYTES:
        raise ValueError('backup manifest exceeds size limit')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        raise ValueError('backup manifest changed or is unsafe') from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or _manifest_identity(before) != _manifest_identity(opened):
            raise ValueError('backup manifest changed or is unsafe')
        raw = bytearray()
        while len(raw) <= _MAX_MANIFEST_BYTES:
            block = os.read(fd, min(64 * 1024, _MAX_MANIFEST_BYTES + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        if len(raw) > _MAX_MANIFEST_BYTES:
            raise ValueError('backup manifest exceeds size limit')
        after = os.fstat(fd)
        linked = path.lstat()
        if (not stat.S_ISREG(linked.st_mode) or
            _manifest_identity(opened) != _manifest_identity(after) or
            _manifest_identity(opened) != _manifest_identity(linked) or
            len(raw) != opened.st_size):
            raise ValueError('backup manifest changed during verification')
        return bytes(raw)
    finally:
        os.close(fd)


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
        raw = _read_manifest(args.manifest)
        if hashlib.sha256(raw).hexdigest() != args.expected_manifest_sha256:
            raise ValueError('backup manifest digest mismatch')
        report = verify(args.root, json.loads(raw, object_pairs_hook=_unique_object))
    except (OSError, ValueError) as error:
        report = {'decision': DECISION, 'install_allowed': False, 'input_error': str(error)}
    print(json.dumps(report, sort_keys=True))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
