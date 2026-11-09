#!/usr/bin/env python3
"""Offline, static preflight for exact-source MVL stock QCOM model captures.

This never unpickles or runs a model. A PASS binds bytes and build inputs; it
is not a device execution or install qualification.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import pickletools
import re
import stat
import struct
import subprocess

MODEL_DIR = Path('openpilot/selfdrive/modeld/models')
ONNX = ('dmonitoring_model.onnx', 'driving_supercombo.onnx')
ARTIFACTS = (
    'dmonitoring_model_tinygrad.pkl', 'driving_tinygrad.pkl',
    'driving_warp_1344x760_tinygrad.pkl', 'driving_warp_1928x1208_tinygrad.pkl',
    'dm_warp_1344x760_tinygrad.pkl', 'dm_warp_1928x1208_tinygrad.pkl',
)
SOURCE_FILES = (
    'openpilot/selfdrive/modeld/SConscript',
    'openpilot/common/transformations/camera.py',
    'openpilot/common/transformations/model.py',
    'openpilot/system/camerad/cameras/nv12_info.py',
)
COMPILER_DIRS = ('tinygrad', 'extra', 'examples/openpilot')
COMPILER_SUFFIXES = {'.py', '.c', '.cc', '.cpp', '.h', '.hpp', '.cl', '.json'}
LFS_HEADER = 'version https://git-lfs.github.com/spec/v1'
AGNOS_SHA256 = '98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8'
AGNOS199_IMAGE_SHA256 = '80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7'
AGNOS199_MANIFEST_SHA256 = 'c581f89ea1fa16814c4f1965cb2113d2e8c628dfa88d5f210bf2f0917cad6693'
MAX_PICKLE_OPCODES = 100_000_000
MAX_PICKLE_OPERATIONS = 2_000_000
MAX_CAPTURE_BYTES = 1024 ** 3


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def regular(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'missing or non-regular file: {path}')
    return path


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()


def source_identity(root: Path) -> tuple[str, str]:
    head = git(root, 'rev-parse', '--verify', 'HEAD')
    row = git(root, 'ls-tree', 'HEAD', 'tinygrad_repo').split()
    if len(row) < 3 or row[:2] != ['160000', 'commit']:
        raise ValueError('tinygrad_repo is not pinned by a Git submodule link')
    link = row[2]
    compiler = root / 'tinygrad_repo'
    if git(compiler, 'rev-parse', '--verify', 'HEAD') != link:
        raise ValueError('materialized tinygrad compiler differs from source Git link')
    if subprocess.call(['git', '-C', str(root), 'diff', '--quiet', 'HEAD', '--', *SOURCE_FILES]) != 0:
        raise ValueError('tracked MVL model build inputs differ from source commit')
    if subprocess.call(['git', '-C', str(compiler), 'diff', '--quiet', 'HEAD', '--', *COMPILER_DIRS]) != 0:
        raise ValueError('tracked tinygrad compiler differs from Git link')
    untracked = git(compiler, 'ls-files', '--others', '--exclude-standard', '--', *COMPILER_DIRS).splitlines()
    if any(Path(name).suffix in COMPILER_SUFFIXES for name in untracked):
        raise ValueError('untracked compiler source would break exact source identity')
    return head, link


def lfs_identity(pointer: Path, blob: Path) -> dict:
    regular(pointer)
    regular(blob)
    data = pointer.read_bytes()
    if data.startswith(LFS_HEADER.encode()):
        lines = data.decode('ascii').splitlines()
        if len(lines) != 3 or lines[0] != LFS_HEADER or not lines[1].startswith('oid sha256:') or not lines[2].startswith('size '):
            raise ValueError(f'invalid ONNX LFS pointer: {pointer}')
        digest = lines[1].removeprefix('oid sha256:')
        if not re.fullmatch('[0-9a-f]{64}', digest) or not lines[2][5:].isdigit():
            raise ValueError(f'invalid ONNX LFS identity: {pointer}')
        size = int(lines[2][5:])
    else:
        digest, size = sha256(pointer), pointer.stat().st_size
    with blob.open('rb') as stream:
        is_pointer = stream.read(len(LFS_HEADER)) == LFS_HEADER.encode()
    if blob.stat().st_size != size or sha256(blob) != digest or is_pointer:
        raise ValueError(f'ONNX bytes differ from pinned LFS identity: {blob}')
    return {'sha256': digest, 'size': size}


def qcom_capture(path: Path, *, dir_fd: int | None = None) -> dict:
    """Inspect and hash one held regular inode without executing its pickle.

    dir_fd lets a caller pin the artifact directory as well. Every structural
    read and the final digest comes from this same no-follow descriptor.
    """
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path.name if dir_fd is not None else path, flags,
                     **({'dir_fd': dir_fd} if dir_fd is not None else {}))
    except OSError as exc:
        raise ValueError(f'missing or non-regular capture: {path}') from exc
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_CAPTURE_BYTES:
            raise ValueError(f'nonregular, empty or oversized capture: {path}')
        header = stream.read(8)
        if len(header) != 8 or header.startswith(LFS_HEADER.encode()[:8]):
            raise ValueError(f'not a captured model artifact: {path}')
        if header.startswith(b'\x80'):
            stream.seek(0)
            opcodes = stream.read(MAX_PICKLE_OPCODES + 1)
        else:
            length = struct.unpack('<q', header)[0]
            if not 0 < length <= MAX_PICKLE_OPCODES:
                raise ValueError(f'invalid pickle opcode length: {path}')
            opcodes = stream.read(length)
            if len(opcodes) != length:
                raise ValueError(f'truncated pickle opcodes: {path}')
        if len(opcodes) > MAX_PICKLE_OPCODES:
            raise ValueError(f'pickle opcode bound exceeded: {path}')
        wanted = {'QCOM', 'metadata', 'run', 'input_specs', 'output_specs',
                  'output_slices', 'input_shapes'}
        tokens: set[str] = set()
        recent = deque(maxlen=4)
        tinyjit_global = captured_global = False
        last_opcode = None
        count = 0
        try:
            for op, arg, _ in pickletools.genops(opcodes):
                count += 1
                if count > MAX_PICKLE_OPERATIONS:
                    raise ValueError('pickle operation bound exceeded')
                last_opcode = op.name
                if isinstance(arg, str):
                    if arg in wanted:
                        tokens.add(arg)
                    if arg in ('METAL', 'AMD') or arg.startswith(('METAL:', 'AMD:', 'USB+AMD')):
                        raise ValueError('foreign GPU backend')
                if op.name == 'STACK_GLOBAL':
                    names = [value for value in recent if isinstance(value, str)]
                    tinyjit_global |= len(names) >= 2 and names[-2:] == ['tinygrad.engine.jit', '_TinyJit']
                    captured_global |= bool(names) and names[-1] == 'CapturedJit'
                recent.append(arg if isinstance(arg, str) else None)
        except (ValueError, EOFError) as exc:
            raise ValueError(f'malformed pickle opcodes: {path}: {exc}') from exc
        if last_opcode != 'STOP' or not {'QCOM', 'metadata', 'run', 'input_specs'} <= tokens:
            raise ValueError(f'missing QCOM capture structure: {path}')
        if not tinyjit_global or not captured_global:
            raise ValueError(f'missing TinyJit capture globals: {path}')
        if path.name.startswith(('dmonitoring_model_', 'driving_tinygrad')):
            if not {'output_specs', 'output_slices', 'input_shapes'} <= tokens:
                raise ValueError(f'missing model output specification: {path}')
            if before.st_size <= 8 + len(opcodes):
                raise ValueError(f'missing out-of-band model buffers: {path}')
        stream.seek(0)
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                       after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError(f'capture changed during inspection: {path}')
        return {'sha256': digest.hexdigest(), 'size': before.st_size}


def source_hashes(root: Path) -> dict[str, str]:
    paths = [Path(name) for name in SOURCE_FILES]
    for part in COMPILER_DIRS:
        base = root / 'tinygrad_repo' / part
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f'missing compiler directory: {base}')
        paths.extend(path.relative_to(root) for path in base.rglob('*') if path.is_file() and path.suffix in COMPILER_SUFFIXES and '__pycache__' not in path.parts)
    if len(paths) <= len(SOURCE_FILES):
        raise ValueError('empty compiler source inventory')
    return {p.as_posix(): sha256(regular(root / p)) for p in sorted(set(paths))}


def agnos_identity(agnos_image: Path, agnos_root: Path, version: str = '19.8.1', component_manifest: Path | None = None) -> dict:
    if version not in ('19.8.1', '19.9'):
        raise ValueError('unsupported AGNOS version')
    if regular(agnos_root / 'VERSION').read_text().strip() != version or (agnos_root / 'AGNOS').is_symlink() or not (agnos_root / 'AGNOS').is_file():
        raise ValueError(f'AGNOS root is not version {version}')
    image_sha = sha256(regular(agnos_image))
    if version == '19.8.1':
        if component_manifest is not None:
            raise ValueError('19.8.1 does not accept a 19.9 component manifest')
        if image_sha != AGNOS_SHA256:
            raise ValueError('AGNOS image differs from pinned 19.8.1 reference')
        return {'version': version, 'image_sha256': image_sha}
    if component_manifest is None:
        raise ValueError('19.9 requires pinned component manifest')
    try:
        from tools.release.agnos_image import pinned_system
    except ModuleNotFoundError:
        from agnos_image import pinned_system
    part = pinned_system(component_manifest, AGNOS199_MANIFEST_SHA256)
    if part['hash_raw'] != AGNOS199_IMAGE_SHA256 or image_sha != part['hash_raw']:
        raise ValueError('AGNOS image differs from pinned 19.9 reference')
    return {'version': version, 'image_sha256': image_sha, 'component_manifest_sha256': AGNOS199_MANIFEST_SHA256}


def inventory(root: Path, assets: Path, artifacts: Path, agnos_image: Path, agnos_root: Path,
              agnos_version: str = '19.8.1', agnos_component_manifest: Path | None = None) -> dict:
    root = root.resolve()
    head, tinygrad_link = source_identity(root)
    agnos = agnos_identity(agnos_image, agnos_root, agnos_version, agnos_component_manifest)
    result = {
        'version': 1,
        'source_commit': head,
        'tinygrad_gitlink': tinygrad_link,
        'agnos': agnos,
        'source_files': source_hashes(root),
        'onnx': {name: lfs_identity(root / MODEL_DIR / name, assets / name) for name in ONNX},
        'artifacts': {name: qcom_capture(artifacts / name) for name in ARTIFACTS},
    }
    if set(artifacts.iterdir()) != {artifacts / name for name in ARTIFACTS}:
        raise ValueError('unexpected or incomplete model artifact set')
    return result


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate manifest key: {key}')
        result[key] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('record', 'verify'))
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--onnx-assets', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--agnos-image', type=Path, required=True)
    parser.add_argument('--agnos-root', type=Path, required=True)
    parser.add_argument('--agnos-version', choices=('19.8.1', '19.9'), default='19.8.1')
    parser.add_argument('--agnos-component-manifest', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    actual = inventory(args.source, args.onnx_assets, args.artifacts, args.agnos_image, args.agnos_root,
                       args.agnos_version, args.agnos_component_manifest)
    if args.action == 'record':
        if args.manifest.exists():
            parser.error('manifest already exists; preserve original provenance')
        args.manifest.write_text(json.dumps(actual, sort_keys=True, indent=2) + '\n')
        print(f'recorded static QCOM package for {actual["source_commit"]}; device execution unverified')
    else:
        expected = json.loads(regular(args.manifest).read_text(), object_pairs_hook=no_duplicate_keys)
        if expected != actual:
            raise ValueError('manifest, source, AGNOS, ONNX or artifact identity differs')
        print(f'static QCOM package PASS for {actual["source_commit"]}; device execution unverified')


if __name__ == '__main__':
    main()
