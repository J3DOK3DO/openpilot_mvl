#!/usr/bin/env python3
"""Build and verify a deterministic, non-installable C9 read-only device kit."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import tempfile

FROZEN_SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
PLAN_SHA256 = '6a493a0d9418f62310ee9a0f33d8e50ade4d5dc768cd54ec9c20ad45eaf3cd6e'
PREFLIGHT_SHA256 = 'c04d47fd2e07f8bac34c7c53b852e8b48d3367ed269999fed0eb7d9f358b3537'
ARTIFACT_ROOT = Path('/mnt/commadrive/MVL_C9_B3_G10_R0_ARTIFACTS_20261109')
FILES = (
    'tools/release/c9_b3_pilot.py',
    'tools/release/c9_b3_receipt.py',
    'tools/release/mvl_model_artifacts.py',
    'tools/release/qcom_b3_prepare.py',
    'tools/release/qcom_b2final.py',
    'tools/release/agnos_image.py',
    'tools/release/preflight_readonly.py',
    'docs/engineering/autonomous_campaign/B3_SIX_TARGET_DRY_RUN_20261107.json',
    'tools/release/c9_b3_windows_pilot.ps1',
)
MANIFEST_MEMBER = 'manifest.json'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def safe_member(name: str) -> None:
    parts = PurePosixPath(name).parts
    if not name or name.startswith('/') or '\\' in name or any(x in ('', '.', '..') for x in parts):
        raise ValueError('unsafe kit member path: ' + name)
    if PurePosixPath(name).as_posix() != name:
        raise ValueError('noncanonical kit member path: ' + name)


def regular_input(repo: Path, rel: str) -> bytes:
    safe_member(rel)
    path = repo
    for part in PurePosixPath(rel).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('symlink package input: ' + rel)
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.stat().st_nlink != 1:
        raise ValueError('nonregular package input: ' + rel)
    data = path.read_bytes()
    if data != git(repo, 'show', 'HEAD:' + rel):
        raise ValueError('package input differs from committed HEAD: ' + rel)
    return data


def check_dependencies(blobs: dict[str, bytes]) -> None:
    """Fail if a packaged Python module gains an unlisted release-local import."""
    for rel, data in blobs.items():
        if not rel.endswith('.py'):
            continue
        tree = ast.parse(data, filename=rel)
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module == 'tools.release':
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('tools.release.'):
                names = [node.module.removeprefix('tools.release.').split('.')[0]]
            elif isinstance(node, ast.Import):
                names = [alias.name.removeprefix('tools.release.').split('.')[0]
                         for alias in node.names if alias.name.startswith('tools.release.')]
            for name in names:
                if 'tools/release/' + name + '.py' not in blobs:
                    raise ValueError('stale dependency list: ' + name)
    if digest(blobs['tools/release/preflight_readonly.py']) != PREFLIGHT_SHA256:
        raise ValueError('trusted preflight hash mismatch')
    if digest(blobs['docs/engineering/autonomous_campaign/B3_SIX_TARGET_DRY_RUN_20261107.json']) != PLAN_SHA256:
        raise ValueError('pinned six-target plan hash mismatch')


def manifest_bytes(manifest: dict) -> bytes:
    return (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()


def tar_add(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    safe_member(name)
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    tar.addfile(info, io.BytesIO(data))


def verify(tar_path: Path, manifest: dict) -> None:
    expected = {row['path']: row for row in manifest['files']}
    expected[MANIFEST_MEMBER] = {'sha256': digest(manifest_bytes(manifest)),
                                 'bytes': len(manifest_bytes(manifest))}
    payload_blocks = sum(512 + ((row['bytes'] + 511) // 512) * 512 for row in expected.values())
    expected_size = ((payload_blocks + 1024 + 10239) // 10240) * 10240
    if tar_path.stat().st_size != expected_size:
        raise ValueError('kit tar size or trailing data mismatch')
    with tarfile.open(tar_path, 'r:') as tar:
        members = tar.getmembers()
        if [m.name for m in members] != list(expected):
            raise ValueError('kit member set or order mismatch')
        for member in members:
            safe_member(member.name)
            if not member.isfile() or member.mode != 0o644 or member.mtime != 0 or member.uid or member.gid:
                raise ValueError('unsafe kit member metadata: ' + member.name)
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError('missing kit member data: ' + member.name)
            data = stream.read()
            row = expected[member.name]
            if len(data) != row['bytes'] or digest(data) != row['sha256']:
                raise ValueError('kit member hash mismatch: ' + member.name)


def build(repo: Path, output: Path, artifact_root: Path = ARTIFACT_ROOT) -> dict:
    repo = repo.absolute()
    output = output.absolute()
    if output.exists() or output.is_symlink() or output.with_suffix('.json').exists():
        raise ValueError('kit output already exists')
    if output.suffix != '.tar' or output.parent.is_symlink() or not output.parent.resolve().is_relative_to(artifact_root.resolve()):
        raise ValueError('kit tar must be under C9 artifacts')
    if Path(os.fsdecode(git(repo, 'rev-parse', '--show-toplevel').strip())).resolve() != repo.resolve():
        raise ValueError('repo must be the Git worktree root')
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    if head == FROZEN_SOURCE:
        raise ValueError('engineering checkout confused with frozen source')
    if git(repo, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('uncommitted source differences in engineering worktree')
    blobs = {rel: regular_input(repo, rel) for rel in FILES}
    check_dependencies(blobs)
    rows = [{'path': rel, 'sha256': digest(data), 'bytes': len(data)} for rel, data in blobs.items()]
    manifest = {'schema_version': 1, 'classification': 'NOT_INSTALLABLE_READ_ONLY_PREFLIGHT_KIT',
                'warning': 'Not installable; read-only preflight only. Physical GPU execution remains blocked.',
                'install_allowed': False, 'execution_authorized': False, 'engineering_head': head,
                'frozen_product_source_commit': FROZEN_SOURCE, 'files': rows,
                'b3_verified_outputs': 0, 'g10_product': 'NOT_BUILT', 'physical_checks_passed': 0}
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.c9-kit-', suffix='.tar', delete=False) as stream:
        temp = Path(stream.name)
    try:
        with tarfile.open(temp, 'w', format=tarfile.USTAR_FORMAT) as tar:
            for rel, data in blobs.items():
                tar_add(tar, rel, data)
            tar_add(tar, MANIFEST_MEMBER, manifest_bytes(manifest))
        verify(temp, manifest)
        # Re-read committed inputs before publishing, so an intervening edit fails closed.
        if git(repo, 'rev-parse', 'HEAD').decode().strip() != head or git(repo, 'status', '--porcelain', '--untracked-files=all').strip():
            raise ValueError('engineering HEAD or worktree changed during build')
        if any(regular_input(repo, rel) != data for rel, data in blobs.items()):
            raise ValueError('package input changed during build')
        manifest_path = output.with_suffix('.json')
        manifest_path.write_bytes(manifest_bytes(manifest))
        temp.replace(output)
        verify(output, manifest)
        return {**manifest, 'tar_path': str(output), 'tar_sha256': digest(output.read_bytes()),
                'manifest_path': str(manifest_path), 'manifest_sha256': digest(manifest_path.read_bytes())}
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.repo, args.output)
        code = 0
    except (OSError, ValueError, subprocess.SubprocessError, SyntaxError, tarfile.TarError) as exc:
        result, code = {'decision': 'HOLD', 'install_allowed': False, 'error': str(exc)}, 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
