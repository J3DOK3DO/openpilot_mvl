#!/usr/bin/env python3
"""Coordinator-operated, one-target QCOM pilot. Default mode only checks inputs.

The monitor is a separately supplied executable. Its JSON observations are an
operational interlock, not independent evidence for B3 admission.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import time

from tools.release import mvl_model_artifacts as model
from tools.release.qcom_b3_prepare import FLAGS, FIRST, SOURCE, TINYGRAD

PLAN = Path(__file__).resolve().parents[2] / 'docs/engineering/autonomous_campaign/B3_SIX_TARGET_DRY_RUN_20261107.json'
PLAN_SHA256 = '6a493a0d9418f62310ee9a0f33d8e50ade4d5dc768cd54ec9c20ad45eaf3cd6e'
FIRST_TARGET = 'openpilot/selfdrive/modeld/models/' + FIRST
EXPECTED_ONNX = {
    'dmonitoring_model.onnx': 'dee5a294e8afaacc9295ac5d100e00733ecac278e79264b96331e40a3ede1b04',
    'driving_supercombo.onnx': '65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce',
}
RECIPE = {
    'openpilot/selfdrive/modeld/SConscript': '07499bf98dafa501025e08f71c1819787b5dac9f681d443cb0557a1a9d0d7097',
    'tinygrad_repo/examples/openpilot/compile_onnx.py': '512571a84dc7931a07713a81b342e5087c41b173edea2d9a3b209fb83c5ab340',
    'tinygrad_repo/examples/openpilot/compile_warp.py': '97a6814fde7f16e1ce265c6b6388cd5799c8e2f8969ac78cfc4fd5a929b1921d',
}
TRUSTED_PREFLIGHT = Path(__file__).resolve().with_name('preflight_readonly.py')
MIN_RESERVE = 8 * 1024**3
MAX_SECONDS = 300


def checked_plan() -> dict:
    if model.sha256(model.regular(PLAN)) != PLAN_SHA256:
        raise ValueError('pinned six-target plan hash mismatch')
    plan = json.loads(PLAN.read_bytes(), object_pairs_hook=model.no_duplicate_keys)
    targets = plan['targets']
    if (plan['source_commit'] != SOURCE or plan['tinygrad_commit'] != TINYGRAD or
            plan['qcom_flags'] != FLAGS or plan['agnos']['image_sha256'] != model.AGNOS199_IMAGE_SHA256 or
            [t['order'] for t in targets] != list(range(1, 7)) or
            [t['artifact'] for t in targets] != [FIRST, 'dmonitoring_model_tinygrad.pkl',
                'driving_tinygrad.pkl', 'driving_warp_1928x1208_tinygrad.pkl',
                'dm_warp_1344x760_tinygrad.pkl', 'dm_warp_1928x1208_tinygrad.pkl'] or
            targets[0]['stock_scons_target'] != FIRST_TARGET):
        raise ValueError('pinned six-target plan mismatch')
    return plan


def preflight(source: Path, scratch: Path) -> dict:
    plan = checked_plan()
    if source.resolve() == Path('/data/openpilot') or source.resolve().is_relative_to(Path('/data/openpilot')):
        raise ValueError('active source is forbidden')
    if not source.is_absolute() or not scratch.is_absolute():
        raise ValueError('absolute source and scratch paths required')
    if not str(source.resolve()).startswith('/data/mvl-builds/' + SOURCE + '/'):
        raise ValueError('source must be the isolated frozen device copy')
    if (scratch.resolve() == source.resolve() or scratch.resolve().is_relative_to(source.resolve()) or
            not scratch.resolve().is_relative_to(Path('/data/mvl-builds')/SOURCE) or
            scratch.resolve().is_relative_to(Path('/data/openpilot'))):
        raise ValueError('scratch must be isolated outside source')
    if source.is_symlink() or not source.is_dir():
        raise ValueError('regular isolated source directory required')
    if model.git(source, 'rev-parse', 'HEAD') != SOURCE or model.git(source/'tinygrad_repo', 'rev-parse', 'HEAD') != TINYGRAD:
        raise ValueError('source or compiler commit mismatch')
    check = subprocess.run(['python3', str(TRUSTED_PREFLIGHT), '--repo', str(source),
                            '--commit', SOURCE], capture_output=True, text=True, timeout=120)
    if check.returncode or json.loads(check.stdout).get('result') != 'PASS':
        raise ValueError('full frozen source preflight failed')
    for rel, digest in {**RECIPE, **{'openpilot/selfdrive/modeld/models/'+k: v for k,v in EXPECTED_ONNX.items()}}.items():
        if model.sha256(model.regular(source/rel)) != digest:
            raise ValueError('source input hash mismatch: ' + rel)
    if (source/FIRST_TARGET).exists():
        raise ValueError('first target already exists; refuse overwrite')
    return {'decision': 'READ_ONLY_PREFLIGHT_PASS_EXECUTION_NOT_AUTHORIZED',
            'source_commit': SOURCE, 'tinygrad_commit': TINYGRAD,
            'plan_sha256': PLAN_SHA256, 'first_target': FIRST_TARGET,
            'stock_flags': FLAGS, 'compiler_identity': 'DEVICE_NOT_CAPTURED',
            'runtime_identity': 'DEVICE_NOT_CAPTURED', 'device_write_performed': False}


def observation(command: Path) -> dict:
    result = subprocess.run([str(command)], capture_output=True, text=True, timeout=5, check=True)
    item = json.loads(result.stdout, object_pairs_hook=model.no_duplicate_keys)
    if type(item) is not dict:
        raise ValueError('monitor observation must be an object')
    required = ('stationary', 'physically_disconnected', 'offroad', 'external_power_stable',
                'thermal_within_limit', 'gpu_error_free', 'abort_ready', 'stock_manager_healthy',
                'authenticated')
    if any(item.get(k) is not True for k in required):
        raise ValueError('live monitor unsafe or incomplete')
    if any(item.get(k) is not False for k in ('panda_ignition_can', 'panda_ignition_line', 'engaged')):
        raise ValueError('ignition or engagement unverified')
    if item.get('speed_mps') != 0 or type(item.get('speed_mps')) not in (int, float):
        raise ValueError('zero speed unverified')
    for key in ('cpu_temp_c', 'gpu_temp_c'):
        val = item.get(key)
        if type(val) not in (int, float) or not math.isfinite(val) or not 0 <= val < 70:
            raise ValueError('CPU/GPU thermal unsafe or unknown')
    duration = item.get('external_power_duration_seconds')
    if (type(item.get('gpu_errors')) is not int or item['gpu_errors'] != 0 or
            type(item.get('memory_oom_events')) is not int or item['memory_oom_events'] != 0 or
            type(duration) not in (int, float) or not math.isfinite(duration) or duration < 300):
        raise ValueError('GPU, memory or sustained power evidence missing')
    stamp = datetime.fromisoformat(item['observed_at_utc'].replace('Z', '+00:00'))
    if stamp.tzinfo is None or abs((datetime.now(timezone.utc)-stamp).total_seconds()) > 5:
        raise ValueError('stale monitor observation')
    return item


def execute(source: Path, scratch: Path, gate_path: Path, monitor: Path, log_path: Path) -> dict:
    preflight(source, scratch)
    gate = json.loads(model.regular(gate_path).read_bytes(), object_pairs_hook=model.no_duplicate_keys)
    if type(gate) is not dict:
        raise ValueError('physical gate must be an object')
    required = ('coordinator_approved', 'independent_physical_monitor_qualified',
                'sustained_external_power_qualified', 'thermal_gpu_monitor_qualified',
                'cgroup_abort_rehearsed', 'stock_safety_qualified', 'rollback_ready',
                'aggregate_hard_quota_qualified')
    if any(gate.get(k) is not True for k in required):
        raise ValueError('physical gate incomplete')
    if gate.get('source_commit') != SOURCE or gate.get('target') != FIRST_TARGET or gate.get('max_seconds') != 300:
        raise ValueError('gate is not bound to first target and source')
    if not monitor.is_absolute() or monitor.is_symlink() or not monitor.is_file() or not os.access(monitor, os.X_OK):
        raise ValueError('separate executable monitor required')
    if model.sha256(monitor) != gate.get('monitor_sha256'):
        raise ValueError('monitor digest differs from gate')
    if scratch.exists() and (scratch.is_symlink() or any(scratch.iterdir())):
        raise ValueError('scratch must be empty, non-symlink directory')
    parent = scratch.parent
    if type(gate.get('peak_scratch_bytes')) is not int or gate['peak_scratch_bytes'] <= 0:
        raise ValueError('measured peak scratch required')
    if (type(gate.get('hard_quota_bytes')) is not int or
            gate['hard_quota_bytes'] < gate['peak_scratch_bytes'] or
            type(gate.get('io_read_bps')) is not int or not 0 < gate['io_read_bps'] <= 20_000_000 or
            type(gate.get('io_write_bps')) is not int or not 0 < gate['io_write_bps'] <= 10_000_000):
        raise ValueError('hard quota or bounded IO rates missing')
    io_device = gate.get('io_device')
    if (type(io_device) is not str or not io_device.startswith('/dev/') or
            '..' in Path(io_device).parts or not stat.S_ISBLK(os.stat(io_device).st_mode)):
        raise ValueError('qualified backing block device required for IO limit')
    if shutil.disk_usage(parent).free < MIN_RESERVE + gate['peak_scratch_bytes']:
        raise ValueError('8 GiB reserve plus measured peak scratch unavailable')
    observation(monitor)
    scratch.mkdir(mode=0o700, exist_ok=True)
    for name in ('home', 'tmp', 'cache'):
        (scratch/name).mkdir(mode=0o700)
    env = {'PATH': '/usr/local/venv/bin:/usr/bin:/bin', 'HOME': str(scratch/'home'),
           'TMPDIR': str(scratch/'tmp'), 'PYTHONDONTWRITEBYTECODE': '1'}
    env.update(dict(part.split('=', 1) for part in FLAGS.split()))
    command = ['systemd-run', '--user', '--scope', '--wait', '--collect', '--pipe',
               '--unit=c9-b3-first-warp', '-p', 'MemoryMax=2000M', '-p', 'CPUQuota=100%',
               '-p', 'TasksMax=64', '-p', 'IOWeight=100',
               '-p', f"IOReadBandwidthMax={io_device} {gate['io_read_bps']}",
               '-p', f"IOWriteBandwidthMax={io_device} {gate['io_write_bps']}",
               '-p', 'RuntimeMaxSec=300',
               '/usr/local/venv/bin/python3', '-m', 'SCons', '-j1', '--minimal',
               'cache_dir='+str(scratch/'cache'), FIRST_TARGET]
    started = time.monotonic()
    with log_path.open('xb') as log:
        proc = subprocess.Popen(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            while proc.poll() is None:
                if time.monotonic()-started > MAX_SECONDS:
                    raise TimeoutError('first warp exceeded 300 seconds')
                observation(monitor)
                if shutil.disk_usage(parent).free < MIN_RESERVE:
                    raise ValueError('storage reserve breached')
                time.sleep(2)
        except (Exception, KeyboardInterrupt):
            subprocess.run(['systemctl', '--user', 'stop', 'c9-b3-first-warp.scope'], timeout=10, check=False)
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            raise
    output = source/FIRST_TARGET
    identity = model.qcom_capture(output) if proc.returncode == 0 else None
    return {'decision': 'NATIVE_PILOT_EXECUTED_REQUIRES_INDEPENDENT_AUTHENTICATION',
            'compiler_exit_code': proc.returncode, 'elapsed_seconds': time.monotonic()-started,
            'sha256': identity['sha256'] if identity else None,
            'bytes': identity['size'] if identity else None,
            'compiler_log_sha256': model.sha256(log_path),
            'source_commit': SOURCE, 'tinygrad_commit': TINYGRAD,
            'target': FIRST_TARGET, 'artifact': FIRST, 'gpu_backend': 'QCOM',
            'runtime_inference': 'NOT_TESTED',
            'receipt_authentication': 'SELF_REPORTED_NOT_AUTHENTICATED'}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--scratch', type=Path, required=True)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--gate', type=Path)
    ap.add_argument('--monitor', type=Path)
    ap.add_argument('--log', type=Path)
    args = ap.parse_args()
    try:
        if args.execute:
            if not all((args.gate, args.monitor, args.log)):
                raise ValueError('--execute requires --gate, --monitor and --log')
            result = execute(args.source, args.scratch, args.gate, args.monitor, args.log)
            code = 0 if result['compiler_exit_code'] == 0 else 2
        else:
            result, code = preflight(args.source, args.scratch), 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, TimeoutError) as exc:
        result, code = {'decision': 'HOLD', 'reason': str(exc), 'device_write_performed': False}, 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
