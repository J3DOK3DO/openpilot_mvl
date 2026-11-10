#!/usr/bin/env python3
"""Campaign 13 offline display inventory and non-installable handoff. Never runs UI."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

PARENT = '01b2a79367c2b6f33fa764a0c7a8e9e4e63a2392'
BRANCH = 'codex/mvl-c13-optiona-ui-bench-20261110'
SOURCE_COMMIT = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263')
AGNOS = Path('/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs')
ARTIFACTS = Path('/mnt/commadrive/MVL_C13_OPTIONA_UI_ARTIFACTS_20261110')
UI_FILES = (
    'openpilot/selfdrive/ui/ui.py',
    'openpilot/selfdrive/ui/sunnypilot/layouts/home.py',
    'openpilot/selfdrive/ui/tests/test_starpilot_native_status.py',
    'openpilot/sunnypilot/starpilot_bridge/models.py',
)
STATUS_SCRIPT = '''#!/usr/bin/env python3
"""Read a Campaign 13 inventory. This cannot launch any UI or car service."""
import json
from pathlib import Path
p = Path(__file__).with_name("manifest.json")
m = json.loads(p.read_text(encoding="utf-8"))
assert m["install_allowed"] is False and m["actuation_allowed"] is False
print(json.dumps({k: m[k] for k in ("decision", "install_allowed", "actuation_allowed", "model_runtime_verified", "on_device_qualified")}, sort_keys=True))
'''


def run_git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()


def safe_file(path: Path) -> bytes:
    # All ancestors are checked before open; the final descriptor is no-follow.
    for ancestor in reversed((path, *path.parents)):
        mode = ancestor.lstat().st_mode
        if stat.S_ISLNK(mode) or (ancestor != path and not stat.S_ISDIR(mode)):
            raise ValueError(f'unsafe ancestor: {ancestor}')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f'nonregular file: {path}')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_output(path: Path, directory: bool = False) -> Path:
    if '..' in path.parts or not path.is_absolute():
        raise ValueError('output must be an absolute path without traversal')
    if path.parent != ARTIFACTS or path == ARTIFACTS:
        raise ValueError('output must be a direct child of the C13 artifacts directory')
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    # Reject a replaced evidence root or symlink parent.
    for ancestor in reversed((path.parent, *path.parent.parents)):
        mode = ancestor.lstat().st_mode
        if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
            raise ValueError(f'unsafe output ancestor: {ancestor}')
    return path


def inventory(root: Path = ROOT, source: Path = SOURCE, agnos: Path = AGNOS,
              dependencies: dict[str, bool] | None = None) -> dict:
    if (run_git(root, 'merge-base', 'HEAD', PARENT) != PARENT or
            run_git(root, 'branch', '--show-current') != BRANCH):
        raise ValueError('wrong C13 parent or branch')
    if run_git(source, 'rev-parse', 'HEAD') != SOURCE_COMMIT:
        raise ValueError('wrong frozen source commit')
    version = safe_file(agnos / 'VERSION').decode().strip()
    if version != '19.9':
        raise ValueError('AGNOS version mismatch')
    files = []
    for name in UI_FILES:
        actual = safe_file(source / name)
        committed = subprocess.check_output(['git', '-C', str(source), 'show', f'HEAD:{name}'], stderr=subprocess.PIPE)
        if actual != committed:
            raise ValueError(f'frozen source differs from commit: {name}')
        files.append({'path': name, 'sha256': sha(actual), 'size': len(actual), 'role': 'inventory_only'})
    deps = dependencies if dependencies is not None else {name: importlib.util.find_spec(name) is not None
                                                           for name in ('pytest', 'pyray', 'cffi')}
    return {
        'schema_version': 1, 'campaign': 13, 'option': 'A',
        'parent_commit': PARENT, 'branch': BRANCH, 'frozen_source_commit': SOURCE_COMMIT,
        'agnos_version': version, 'ui_files': files, 'host_dependencies': deps,
        'ui_test_ready': all(deps.get(name) is True for name in ('pytest', 'pyray', 'cffi')),
        'literal_ui_preview_verified': False, 'model_runtime_verified': False,
        'on_device_qualified': False, 'install_allowed': False, 'actuation_allowed': False,
        'g10_product': 'NOT_BUILT', 'b3_verified_outputs': 0, 'c4_passed': 0,
        'release_status': 'HOLD', 'decision': 'NON_INSTALLABLE_OFFLINE_INVENTORY_ONLY',
        'excluded': ['production UI entrypoint', 'car services', 'Panda', 'CAN', 'controller', 'modeld', 'release installer'],
    }


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def make_package(preflight: dict, output: Path) -> dict:
    # The caller cannot supply a forged status or stale preflight to build a
    # misleading package. Recheck the pinned source before writing any bytes.
    checked_output(output, directory=True)
    verified = inventory()
    if type(preflight) is not dict or preflight != verified:
        raise ValueError('caller preflight does not match current verified inventory')
    status = STATUS_SCRIPT.encode()
    manifest = dict(verified)
    manifest.update({'install_allowed': False, 'actuation_allowed': False,
                     'release_status': 'HOLD', 'model_runtime_verified': False,
                     'on_device_qualified': False,
                     'package_kind': 'NON_INSTALLABLE', 'entrypoint': 'status.py',
                     'entrypoint_sha256': sha(status), 'entrypoint_size': len(status),
                     'entrypoint_behavior': 'read-only inventory status print; no UI runtime'})
    output.mkdir(mode=0o755)
    try:
        (output / 'status.py').write_bytes(status)
        (output / 'manifest.json').write_bytes(encoded(manifest))
        (output / 'README.txt').write_text('NON-INSTALLABLE offline inventory. status.py only prints HOLD fields. No UI or vehicle service is included.\n')
    except BaseException:
        for child in output.iterdir():
            child.unlink()
        output.rmdir()
        raise
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'package'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output is not None:
            checked_output(args.output)
        report = inventory()
        if args.command == 'package':
            if args.output is None:
                raise ValueError('package requires --output')
            report = make_package(report, args.output)
        elif args.output is not None:
            with args.output.open('xb') as stream:
                stream.write(encoded(report))
        print(json.dumps(report, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'C13 HOLD: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
