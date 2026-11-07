#!/usr/bin/env python3
"""Offline evidence inventory only. No signature trust root or promotion capability."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).absolute().parents[2]
DOCS = ROOT / 'docs/engineering/autonomous_campaign'
PLAN = DOCS / 'B3C_SIX_TARGET_VERIFIED_PLAN_20261107.json'
RECOVERY = DOCS / 'B3C_RECOVERY_STATE_20261107.json'
PLAN_SHA256 = '6a493a0d9418f62310ee9a0f33d8e50ade4d5dc768cd54ec9c20ad45eaf3cd6e'
RECOVERY_SHA256 = 'c2e0249d30074bc96e37eb7803c1f75667158c03b2aab6b4b35bccad85f81761'
SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
LIMIT = 1024 * 1024
DECISION = 'BLOCKED_NATIVE_B3_AND_G10_NOT_INSTALLABLE'
NAMES = (
    'driving_warp_1344x760_tinygrad.pkl', 'dmonitoring_model_tinygrad.pkl',
    'driving_tinygrad.pkl', 'driving_warp_1928x1208_tinygrad.pkl',
    'dm_warp_1344x760_tinygrad.pkl', 'dm_warp_1928x1208_tinygrad.pkl',
)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def regular(path, directory=False):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('symlink/reparse point refused: ' + str(path))
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError('unexpected file type: ' + str(path))
    return info


def local_path(path):
    path = Path(path)
    if str(path).startswith(('\\\\', '//')) or '..' in path.parts:
        raise ValueError('network/device namespace or parent traversal refused')
    if os.name == 'nt':
        for part in path.parts[1:] if path.anchor else path.parts:
            if Path(part).is_reserved() or ':' in part:
                raise ValueError('reserved device name or alternate stream refused')
    return Path(os.path.abspath(path))


class WindowsLocks:
    """Local no-follow handles; read sharing only excludes existing writers too."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.create = self.kernel.CreateFileW
        self.create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.create.restype = wintypes.HANDLE
        self.close = self.kernel.CloseHandle
        self.close.argtypes = [wintypes.HANDLE]
        self.kernel.GetFileInformationByHandleEx.argtypes = [
            wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        self.kernel.GetFinalPathNameByHandleW.argtypes = [
            wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        self.kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        self.invalid = wintypes.HANDLE(-1).value

    def open(self, path, directory):
        # DRIVE_FIXED only: reject mapped remote, removable and unknown roots
        # before any filesystem traversal or metadata lookup.
        if self.kernel.GetDriveTypeW(path.anchor) != 3:
            raise ValueError('non-fixed local drive refused')
        # FILE_LIST_DIRECTORY makes share exclusion effective; attribute-only
        # opens do not participate in Windows read/write share accounting.
        handle = self.create(str(path), 0x81 if directory else 0x80000000,
                             1, None, 3, 0x02200000, None)
        if handle == self.invalid:
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        return handle

    def validate(self, handle, path, directory):
        # FILE_ATTRIBUTE_TAG_INFO checks the held object, not a pathname.
        attrs = (self.ctypes.c_ulong * 2)()
        if not self.kernel.GetFileInformationByHandleEx(handle, 9, attrs, 8):
            raise OSError(self.ctypes.get_last_error(), 'cannot inspect held path')
        if attrs[0] & 0x400 or bool(attrs[0] & 0x10) != directory:
            raise ValueError('held symlink/reparse or unexpected file type')
        buf = self.ctypes.create_unicode_buffer(32768)
        size = self.kernel.GetFinalPathNameByHandleW(handle, buf, len(buf), 0)
        if not size or size >= len(buf):
            raise ValueError('cannot validate final local path')
        expected = str(path).rstrip('\\')
        final = buf.value
        if not final.startswith('\\\\?\\') or final.startswith('\\\\?\\UNC\\'):
            raise ValueError('nonlocal final path refused')
        if os.path.normcase(final[4:].rstrip('\\')) != os.path.normcase(expected):
            raise ValueError('held final path mismatch')


@contextmanager
def locked_directory(path, missing_ok=False):
    """Hold every ancestor through the last metadata check/read; never follow links.

    A missing sparse component ends traversal immediately. POSIX callers use the
    held base fd for all child lookups, including when an ancestor is renamed.
    """
    path = local_path(path)
    held = []
    try:
        if os.name == 'nt':
            api = WindowsLocks()
            for component in [*reversed(path.parents), path]:
                try:
                    handle = api.open(component, True)
                except FileNotFoundError:
                    if not missing_ok:
                        raise
                    yield None
                    return
                held.append((handle, component))
                api.validate(handle, component, True)
            yield path
        else:
            fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            held.append(fd)
            for part in path.parts[1:]:
                try:
                    fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError:
                    if not missing_ok:
                        raise
                    yield None
                    return
                held.append(fd)
            yield fd
    finally:
        if os.name == 'nt':
            try:
                for handle, component in held:
                    api.validate(handle, component, True)
            finally:
                for handle, _ in reversed(held):
                    api.close(handle)
        else:
            for fd in reversed(held):
                os.close(fd)


def checked_info(info):
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('symlink/reparse point refused')
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('nonregular file refused')
    return info


@contextmanager
def locked_path(path):
    path = local_path(path)
    with locked_directory(path.parent) as parent:
        if os.name == 'nt':
            regular(path)  # Parent handles already exclude mutation/traversal.
            api = WindowsLocks()
            handle = api.open(path, False)
            try:
                api.validate(handle, path, False)
                import msvcrt
                fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
                handle = None  # CRT now owns it, including on validation failure.
                with os.fdopen(fd, 'rb') as stream:
                    try:
                        checked_info(os.fstat(stream.fileno()))
                        yield stream
                    finally:
                        api.validate(msvcrt.get_osfhandle(stream.fileno()), path, False)
            finally:
                if handle is not None:
                    api.close(handle)
        else:
            # Reject devices BEFORE any read-open. O_PATH pins a raced-in inode
            # without contacting its driver; procfs reopens that exact held inode.
            checked_info(os.stat(path.name, dir_fd=parent, follow_symlinks=False))
            if not hasattr(os, 'O_PATH'):
                raise ValueError('safe O_PATH/procfs regular-file read unavailable')
            pin = os.open(path.name, os.O_PATH | os.O_NOFOLLOW, dir_fd=parent)
            try:
                info = checked_info(os.fstat(pin))
                final = os.open('/proc/self/fd/' + str(pin), os.O_RDONLY | os.O_NONBLOCK)
                with os.fdopen(final, 'rb') as stream:
                    opened = checked_info(os.fstat(stream.fileno()))
                    if (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino):
                        raise ValueError('held inode mismatch')
                    yield stream
            finally:
                os.close(pin)


def inventory_artifacts(base):
    inventory = {}
    with locked_directory(base, missing_ok=True) as held:
        for name in NAMES:
            if held is None:
                inventory[name] = 'ABSENT_IN_LOCAL_CHECKOUT'
                continue
            try:
                if os.name == 'nt':
                    regular(held / name)
                else:
                    checked_info(os.stat(name, dir_fd=held, follow_symlinks=False))
                inventory[name] = 'PRESENT_UNVERIFIED'
            except FileNotFoundError:
                inventory[name] = 'ABSENT_IN_LOCAL_CHECKOUT'
    return inventory


def load(path, expected_hash=None):
    with locked_path(path) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
            raise ValueError('nonregular or oversized JSON')
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('oversized JSON')
    if expected_hash and hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError('pinned evidence hash mismatch')
    def invalid_constant(value):
        raise ValueError('nonfinite JSON number: ' + value)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                       parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise ValueError('evidence must be a JSON object')
    return value


def evaluate(plan=PLAN, recovery=RECOVERY, claims=None, artifacts=None):
    pinned = load(plan, PLAN_SHA256)
    state = load(recovery, RECOVERY_SHA256)
    if pinned['source_commit'] != SOURCE or state['frozen_source_commit'] != SOURCE:
        raise ValueError('stale source')
    if tuple(target['artifact'] for target in pinned['targets']) != NAMES:
        raise ValueError('six-target identity mismatch')
    issues = []
    if claims is not None:
        claim = load(claims)
        if claim.get('source_commit') != SOURCE:
            raise ValueError('external claim source missing or stale')
        issues.append('EXTERNAL_CLAIMS_UNAUTHENTICATED_NO_TRUST_ROOT')
    # Only inspect the six exact local paths. Never open capture/pickle bytes.
    base = Path(artifacts) if artifacts is not None else ROOT / 'openpilot/selfdrive/modeld/models'
    base = local_path(base)
    inventory = inventory_artifacts(base)
    present = sum(value == 'PRESENT_UNVERIFIED' for value in inventory.values())
    return {
        'schema_version': 1, 'decision': DECISION, 'release_status': 'HOLD',
        'source_commit': SOURCE, 'plan_sha256': PLAN_SHA256,
        'recovery_sha256': RECOVERY_SHA256,
        'evidence_authority': 'PINNED_HISTORICAL_OFFLINE_STATE_ONLY',
        'external_proof_authentication': 'UNSUPPORTED_NO_TRUST_ROOT_OR_SIGNATURE_VALIDATOR',
        'b3_status': 'B3_NATIVE_PROVIDER_MISSING',
        'g10_status': 'G10_PRODUCT_BUILD_INCOMPLETE', 'g10_cold_build': 'NOT_BUILT',
        'rc_status': 'RC_NOT_INSTALLABLE', 'device_status': 'DEVICE_NOT_QUALIFIED',
        'b2_safety_status': 'NOT_SAFETY_ACCEPTED_NOT_PASSED',
        'b2_waiver': state['b2_waiver'],
        'artifact_directory': str(base), 'artifact_inventory': inventory,
        'b3_local_present_count': present, 'b3_static_candidate_count': 0,
        'b3_verified_artifact_count': 0, 'b3_required_artifact_count': 6,
        'b3_completed_6_of_6': False,
        'physical_checks_passed': 0, 'physical_checks_required': 10,
        'independent_combined_review': 'PENDING',
        'blocking_requirements': {
            'native_qcom_provider_and_execution': 'NO_AUTHENTICATED_EVIDENCE',
            'b2_technical_safeguards': 'NO_SAFETY_PROOF',
            'six_exact_source_qcom_outputs': 'NO_AUTHENTICATED_EVIDENCE',
            'cold_complete_agnos199_arm64_product': 'NOT_BUILT',
            'elf_dependencies_and_target_runtime': 'NOT_QUALIFIED',
            'complete_bundle_and_owner_recovery_identity': 'NOT_VERIFIED',
            'independent_combined_review': 'PENDING',
            'physical_comma4_checks': '0_OF_10',
        },
        'install_allowed': False, 'g10_promotion': False,
        'device_access_performed': False, 'device_write_performed': False,
        'issues': issues,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=PLAN)
    parser.add_argument('--recovery', type=Path, default=RECOVERY)
    parser.add_argument('--claims', type=Path, help='untrusted JSON, including claimed signed proofs')
    parser.add_argument('--artifacts', type=Path, help='local offline six-file inventory only')
    args = parser.parse_args(argv)
    try:
        result = evaluate(args.plan, args.recovery, args.claims, args.artifacts)
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({'decision': DECISION, 'install_allowed': False,
                          'release_status': 'HOLD', 'input_error': str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2  # A readable inventory is never a successful release gate.


if __name__ == '__main__':
    raise SystemExit(main())
