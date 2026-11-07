#!/usr/bin/env python3
"""Host-testable, fail-closed B2 safeguards. Device execution stays disabled."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import time

SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
DEVICE_ROOT = Path('/data/mvl-builds')
RUN_RE = re.compile(r'pilot-[0-9a-f]{16}\Z')
GIB = 1024 ** 3
RESERVE = 2 * GIB


@dataclass(frozen=True)
class Sample:
    monotonic: float
    received_at: float
    panda_ignition_can: bool
    panda_ignition_line: bool
    car_parked: bool
    speed_mps: float
    engaged: bool
    panda_fresh: bool
    car_fresh: bool
    controls_fresh: bool
    authenticated: bool


def safe_sample(sample: Sample, now: float) -> list[str]:
    reasons = []
    if sample.authenticated is not True:
        reasons.append('TELEMETRY_UNAUTHENTICATED')
    if any(x is not True for x in (sample.panda_fresh, sample.car_fresh, sample.controls_fresh)):
        reasons.append('REQUIRED_TELEMETRY_MISSING')
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
               for x in (now, sample.received_at, sample.monotonic)) or \
            not 0 <= now - sample.received_at <= 1 or not 0 <= now - sample.monotonic <= 1:
        reasons.append('TELEMETRY_STALE')
    if sample.panda_ignition_can is not False or sample.panda_ignition_line is not False or \
            sample.car_parked is not True or sample.engaged is not False or \
            not isinstance(sample.speed_mps, (int, float)) or isinstance(sample.speed_mps, bool) or \
            not math.isfinite(sample.speed_mps) or sample.speed_mps != 0:
        reasons.append('VEHICLE_NOT_PROVEN_PARKED_OFF')
    return reasons


def preflight(samples: list[Sample], now: float) -> list[str]:
    if len(samples) < 31:
        return ['CONTINUOUS_30_SECOND_PROOF_MISSING']
    times = [x.monotonic for x in samples]
    if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in times) or \
            any(not 0 < b-a <= 1 for a, b in zip(times, times[1:])) or times[-1]-times[0] < 30:
        return ['TELEMETRY_CADENCE_OR_DURATION_INVALID']
    reasons = []
    for i, sample in enumerate(samples):
        observed_at = samples[i+1].monotonic if i+1 < len(samples) else now
        reasons.extend(safe_sample(sample, observed_at))
    return sorted(set(reasons))


def resource_reasons(*, cpu_c: float | None, gpu_c: float | None, mem_available: int | None,
                     data_free: int | None, memory_oom_events: int | None,
                     gpu_errors: int | None, heartbeat_age: float | None,
                     quota_breached: bool | None, foreign_process: bool | None,
                     operator_abort: bool | None, connection_alive: bool | None) -> list[str]:
    reasons = []
    if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or not 0 <= x < 70
           for x in (cpu_c, gpu_c)):
        reasons.append('ACTUAL_THERMAL_UNSAFE_OR_MISSING')
    if not isinstance(mem_available, int) or isinstance(mem_available, bool) or mem_available < 512 * 1024**2:
        reasons.append('MEMORY_HEADROOM_LOW_OR_MISSING')
    if not isinstance(data_free, int) or isinstance(data_free, bool) or data_free < RESERVE:
        reasons.append('DISK_RESERVE_LOW_OR_MISSING')
    if not isinstance(memory_oom_events, int) or isinstance(memory_oom_events, bool) or memory_oom_events > 0:
        reasons.append('OOM_EVENT_OR_COUNTER_MISSING')
    if not isinstance(gpu_errors, int) or isinstance(gpu_errors, bool) or gpu_errors > 0:
        reasons.append('GPU_ERROR_OR_COUNTER_MISSING')
    if not isinstance(heartbeat_age, (int, float)) or isinstance(heartbeat_age, bool) or not math.isfinite(heartbeat_age) or not 0 <= heartbeat_age <= 1:
        reasons.append('WATCHDOG_HEARTBEAT_LOST')
    if quota_breached is not False:
        reasons.append('QUOTA_BREACH_OR_UNKNOWN')
    if foreign_process is not False:
        reasons.append('UNEXPECTED_PROCESS_OR_UNKNOWN')
    if operator_abort is not False:
        reasons.append('OPERATOR_ABORT_OR_UNKNOWN')
    if connection_alive is not True:
        reasons.append('CONTROLLER_CONNECTION_LOST_OR_UNKNOWN')
    return reasons


def pilot_path(run_id: str, root: Path = DEVICE_ROOT) -> Path:
    if not re.fullmatch(r'[0-9a-f]{16}', run_id) or not root.is_absolute() or '..' in root.parts:
        raise ValueError('invalid run id or root')
    return root / SOURCE / ('pilot-' + run_id)


def _mount_id(fd: int) -> str:
    for line in Path(f'/proc/self/fdinfo/{fd}').read_text().splitlines():
        if line.startswith('mnt_id:'):
            return line.split(':', 1)[1].strip()
    raise ValueError('mount identity unavailable')


def _open_verified_directory(path: Path) -> int:
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('unsafe path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _delete_contents(fd: int, expected_mount: str) -> None:
    if _mount_id(fd) != expected_mount:
        raise ValueError('unexpected mount boundary')
    for name in os.listdir(fd):
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise ValueError(f'symlink in isolated tree: {name}')
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                if _mount_id(child) != expected_mount:
                    raise ValueError(f'unexpected mount boundary: {name}')
                _delete_contents(child, expected_mount)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=fd)
        elif stat.S_ISREG(info.st_mode):
            file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                if _mount_id(file_fd) != expected_mount:
                    raise ValueError(f'unexpected file mount: {name}')
            finally:
                os.close(file_fd)
            os.unlink(name, dir_fd=fd)
        else:
            raise ValueError(f'unsupported file type: {name}')


def _check_tree(fd: int, expected_mount: str) -> None:
    if _mount_id(fd) != expected_mount:
        raise ValueError('unexpected mount boundary')
    for name in os.listdir(fd):
        mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
        if stat.S_ISDIR(mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                _check_tree(child, expected_mount)
            finally:
                os.close(child)
        elif stat.S_ISREG(mode):
            file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                if _mount_id(file_fd) != expected_mount:
                    raise ValueError(f'unexpected file mount: {name}')
            finally:
                os.close(file_fd)
        else:
            raise ValueError(f'unsafe file type: {name}')


def cleanup_host_fixture(run_dir: Path, root: Path, run_id: str, nonce: str,
                         *, worker_stopped: bool, preserve_evidence: bool = True) -> dict:
    """Delete only a verified /tmp fixture; device cleanup requires separate code/review."""
    expected = pilot_path(run_id, root)
    if not root.is_relative_to(Path('/tmp')) or run_dir != expected or not RUN_RE.fullmatch(run_dir.name):
        raise ValueError('cleanup path outside exact host fixture')
    if not worker_stopped:
        raise ValueError('worker termination unverified')
    if not run_dir.exists():
        return {'status': 'ALREADY_ABSENT', 'run_id': run_id}
    parent_fd = _open_verified_directory(run_dir.parent)
    try:
        fd = os.open(run_dir.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            mount = _mount_id(fd)
            st = os.fstat(fd)
            owner_fd = os.open('owner.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                owner_stat = os.fstat(owner_fd)
                if not stat.S_ISREG(owner_stat.st_mode) or owner_stat.st_size > 4096:
                    raise ValueError('invalid owner record')
                owner = json.loads(os.read(owner_fd, 4097))
            finally:
                os.close(owner_fd)
            if owner != {'run_id': run_id, 'source': SOURCE, 'nonce': nonce, 'device': st.st_dev, 'inode': st.st_ino}:
                raise ValueError('owner/run identity mismatch')
            evidence = run_dir / 'evidence'
            if preserve_evidence and evidence.exists():
                raise ValueError('evidence present; export and explicitly authorize its removal')
            _check_tree(fd, mount)
            _delete_contents(fd, mount)
        finally:
            os.close(fd)
        if (os.stat(run_dir.name, dir_fd=parent_fd, follow_symlinks=False).st_dev,
            os.stat(run_dir.name, dir_fd=parent_fd, follow_symlinks=False).st_ino) != (st.st_dev, st.st_ino):
            raise ValueError('pilot directory changed during cleanup')
        os.rmdir(run_dir.name, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)
    return {'status': 'REMOVED_VERIFIED_HOST_FIXTURE', 'run_id': run_id}


def stop_owned_process(proc: subprocess.Popen, *, timeout: float = 2) -> str:
    """Stop only a process launched by this controller in its own process group."""
    if proc.poll() is not None:
        return 'ALREADY_STOPPED'
    if os.getpgid(proc.pid) != proc.pid:
        raise ValueError('worker has no dedicated process group')
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=timeout)
    return 'STOPPED_OWNED_GROUP'


def supervise_host_worker(proc: subprocess.Popen, sample_provider, resource_provider,
                          *, max_seconds: float = 5, poll_interval: float = 0.05) -> dict:
    """Host fixture supervisor; provider proof and controller-crash containment are not established."""
    if not 0 < max_seconds <= 60 or not 0 < poll_interval <= 1:
        raise ValueError('invalid bounded host supervision interval')
    deadline = time.monotonic() + max_seconds
    while proc.poll() is None:
        try:
            now = time.monotonic()
            sample = sample_provider()
            reasons = safe_sample(sample, now) + resource_reasons(**resource_provider())
        except BaseException as exc:
            reasons = ['MONITOR_FAILURE_' + type(exc).__name__]
        if time.monotonic() >= deadline:
            reasons.append('COMPILER_TIMEOUT')
        if reasons:
            stop_owned_process(proc)
            return {'decision': 'ABORTED_HOST_FIXTURE', 'reasons': sorted(set(reasons)), 'exit_code': proc.returncode}
        time.sleep(poll_interval)
    return {'decision': 'HOST_FIXTURE_EXITED', 'reasons': [] if proc.returncode == 0 else ['WORKER_NONZERO_EXIT'],
            'exit_code': proc.returncode}


def quota_assessment(*, filesystem: str, project_quota_active: bool, tested_hard_limit: bool,
                     all_writes_confined: bool, requested_bytes: int, measured_source_bytes: int) -> dict:
    if requested_bytes <= 0 or measured_source_bytes <= 0:
        raise ValueError('invalid byte budget')
    enough_for_source = requested_bytes > measured_source_bytes
    enforceable = filesystem in ('ext4', 'xfs') and project_quota_active and tested_hard_limit and all_writes_confined
    return {'candidate_bytes': requested_bytes, 'measured_source_bytes': measured_source_bytes,
            'source_fits_before_scratch': enough_for_source,
            'decision': 'HOST_POLICY_ELIGIBLE_DEVICE_NOT_VERIFIED' if enforceable and enough_for_source else 'NOT_VERIFIED_OR_INSUFFICIENT',
            'device_qualified': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute:
        print(json.dumps({'decision': 'NO_GO_EXECUTION_DISABLED', 'device_write_performed': False}))
        return 2
    try:
        path = pilot_path(args.run_id)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({'decision': 'HOST_PLAN_ONLY', 'path': str(path), 'device_write_performed': False}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
