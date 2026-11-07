#!/usr/bin/env python3
"""Read-only device inspection and host-testable B2 gate. No device write path.

The executable pilot is deliberately unimplemented until a hard storage quota,
independent live vehicle-state proof, and fail-safe monitor are validated on device.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
INSTALLED = 'a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1'
ROOT = Path('/data/mvl-builds')
GIB = 1024 ** 3
PILOT_LIMIT = 512 * 1024 ** 2
RESERVE = 2 * GIB
TARGET = 'openpilot/selfdrive/modeld/models/driving_warp_1344x760_tinygrad.pkl'
FLAGS = 'DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1'


def pilot_path(run_id: str, root: Path = ROOT) -> Path:
    if not re.fullmatch(r'[a-f0-9]{16}', run_id):
        raise ValueError('run id must be 16 lowercase hexadecimal characters')
    if root != ROOT and not root.is_absolute():
        raise ValueError('test root must be absolute')
    return root / SOURCE / ('pilot-' + run_id)


def no_symlink_components(path: Path) -> bool:
    """Check existing components without following a symlink in a proposed path."""
    if not path.is_absolute() or '..' in path.parts:
        return False
    current = Path('/')
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            return False
    return True


def evaluate(e: dict, now: float) -> list[str]:
    """Fixture/telemetry policy. A PASS is only eligibility for a bounded pilot.

    This function cannot authenticate the evidence or prove that the monitor can
    stop a GPU compiler before a transient resource spike.
    """
    blocks: list[str] = []
    def fail_if(condition: bool, label: str) -> None:
        if condition:
            blocks.append(label)

    fail_if(e.get('source_commit') != SOURCE or e.get('source_verified') is not True,
            'SOURCE_IDENTITY_UNVERIFIED')
    fail_if(e.get('installed_commit') != INSTALLED or e.get('installed_untouched') is not True,
            'INSTALLED_IDENTITY_UNVERIFIED')
    fail_if(e.get('agnos') != '19.9' or e.get('model') != 'comma mici', 'DEVICE_IDENTITY_UNVERIFIED')
    fail_if(e.get('handoff_sha_verified') is not True or e.get('submodules_verified') is not True or
            e.get('onnx_verified') is not True, 'SOURCE_CONTENT_UNVERIFIED')
    fail_if(e.get('no_control_or_panda_process') is not True, 'CONTROL_PROCESS_PRESENT_OR_UNKNOWN')
    fail_if(e.get('operator_armed') is not True or e.get('proof_authenticated') is not True,
            'INDEPENDENT_OPERATOR_PROOF_MISSING')
    fail_if(e.get('telemetry_subscription_ok') is not True or e.get('monitor_subscription_ok') is not True,
            'LIVE_TELEMETRY_UNAVAILABLE')
    samples = e.get('samples')
    if not isinstance(samples, list) or len(samples) < 31:
        blocks.append('CONTINUOUS_PARKED_OFF_PROOF_MISSING')
    else:
        try:
            times = [float(s['monotonic']) for s in samples]
            safe = all(s['panda_ignition'] is False and s['car_parked'] is True and
                       s['engaged'] is False and s['panda_fresh'] is True and
                       s['car_state_fresh'] is True for s in samples)
            chronological = times == sorted(times) and len(set(times)) == len(times)
            cadence = all(0 < later - earlier <= 1 for earlier, later in zip(times, times[1:]))
            fresh = 0 <= now - times[-1] <= 5 and times[-1] - times[0] >= 30
            fail_if(not (safe and chronological and cadence and fresh), 'CONTINUOUS_PARKED_OFF_PROOF_MISSING')
        except (KeyError, TypeError, ValueError):
            blocks.append('CONTINUOUS_PARKED_OFF_PROOF_MISSING')
    thermals = e.get('thermal_sensors')
    if not isinstance(thermals, dict) or set(thermals) != {'cpu_actual', 'gpu_actual'} or any(
            not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < 60000 for v in thermals.values()):
        blocks.append('ACTUAL_CPU_GPU_THERMAL_UNVERIFIED')
    mem = e.get('mem_available_bytes')
    fail_if(not isinstance(mem, int) or isinstance(mem, bool) or mem < 2 * GIB,
            'RAM_HEADROOM_UNVERIFIED')
    free = e.get('data_free_bytes')
    fail_if(not isinstance(free, int) or isinstance(free, bool) or free < RESERVE + PILOT_LIMIT,
            'DISK_RESERVE_OR_PILOT_BUDGET_MISSING')
    fail_if(e.get('hard_storage_quota_bytes') != PILOT_LIMIT or
            e.get('quota_enforced_independently') is not True,
            'HARD_STORAGE_QUOTA_UNVERIFIED')
    fail_if(e.get('memory_limit_bytes') != 512 * 1024 ** 2 or
            e.get('memory_limit_enforced') is not True, 'MEMORY_CEILING_UNVERIFIED')
    fail_if(e.get('fresh_monitor_max_age_seconds') != 1 or
            e.get('monitor_abort_on_stale') is not True or e.get('monitor_abort_on_ignition') is not True or
            e.get('monitor_abort_on_engagement') is not True or
            e.get('monitor_abort_on_thermal') is not True or
            e.get('monitor_abort_on_low_disk') is not True or
            e.get('monitor_abort_on_memory') is not True or
            e.get('monitor_abort_on_timeout') is not True or
            e.get('monitor_kill_process_group') is not True or
            e.get('monitor_watchdog_independent') is not True,
            'FAIL_SAFE_MONITOR_UNVERIFIED')
    fail_if(e.get('cpu_affinity_0_7_verified') is not True, 'CPU_AFFINITY_UNVERIFIED')
    path = e.get('pilot_path')
    fail_if(not isinstance(path, str) or not re.fullmatch(
        rf'/data/mvl-builds/{SOURCE}/pilot-[a-f0-9]{{16}}', path) or
        (isinstance(path, str) and not no_symlink_components(Path(path))),
        'ISOLATION_PATH_UNVERIFIED')
    return blocks


def read_git_head(path: Path) -> str | None:
    if not path.is_dir() or path.is_symlink() or not no_symlink_components(path):
        return None
    try:
        p = subprocess.run(['git', '--no-optional-locks', '-C', str(path), 'rev-parse', 'HEAD'],
                           capture_output=True, text=True, timeout=5, check=False,
                           env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def inspect(run_id: str) -> dict:
    """Only stat/read operations. This cannot observe cereal vehicle telemetry."""
    path = pilot_path(run_id)
    result: dict = {'mode': 'READ_ONLY_INSPECT', 'pilot_path': str(path),
                    'source_commit_expected': SOURCE, 'installed_commit_expected': INSTALLED,
                    'source_head': read_git_head(path / 'source'),
                    'installed_head': read_git_head(Path('/data/openpilot')),
                    'path_components_no_symlink': no_symlink_components(path),
                    'device_write_performed': False,
                    'decision': 'NO_GO_LIVE_TELEMETRY_AND_HARD_QUOTA_UNVERIFIED'}
    try:
        fs = os.statvfs('/data')
        result['data_available_bytes'] = fs.f_bavail * fs.f_frsize
    except OSError:
        result['data_available_bytes'] = None
    try:
        lines = Path('/proc/meminfo').read_text().splitlines()
        result['mem_available_bytes'] = next(int(x.split()[1]) * 1024 for x in lines if x.startswith('MemAvailable:'))
    except (OSError, ValueError, StopIteration):
        result['mem_available_bytes'] = None
    return result


def plan(run_id: str) -> dict:
    path = pilot_path(run_id)
    return {'mode': 'READ_ONLY_PLAN', 'decision': 'NO_GO_UNTIL_INDEPENDENT_GATES_PROVEN',
            'pilot_path': str(path), 'single_target': TARGET, 'qcom_flags': FLAGS,
            'cwd': str(path / 'source'), 'unset_environment': ['SKIP_TINYGRAD_COMPILE'],
            'conditional_scons_argv': ['/usr/local/venv/bin/python3', '-m', 'SCons', '-j1',
                                       '--minimal', 'cache_dir=' + str(path / 'cache'), TARGET],
            'environment': {'PATH': '/usr/local/venv/bin:/usr/bin:/bin',
                            'TMPDIR': str(path / 'tmp'), 'HOME': str(path / 'home'),
                            'PYTHONDONTWRITEBYTECODE': '1'},
            'required': ['independent authenticated live pandaStates and carState',
                         'hard per-pilot storage quota and memory limit proven on AGNOS 19.9',
                         'continuous fail-safe monitor and fresh actual CPU/GPU sensors',
                         'exact source with Git metadata and pinned content',
                         'isolated workspace with >=2 GiB remaining /data reserve'],
            'device_write_performed': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--plan', action='store_true')
    group.add_argument('--inspect', action='store_true')
    group.add_argument('--execute', action='store_true')
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    try:
        if args.execute:
            # A self-reported proof file is insufficient: quota and monitor must
            # be independently implemented and audited before writes are possible.
            print(json.dumps({'decision': 'NO_GO_EXECUTION_DISABLED',
                              'reason': 'hard quota and authenticated continuous live-state monitor not implemented',
                              'device_write_performed': False}, sort_keys=True))
            return 2
        print(json.dumps(plan(args.run_id) if args.plan else inspect(args.run_id), indent=2, sort_keys=True))
        return 0
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
