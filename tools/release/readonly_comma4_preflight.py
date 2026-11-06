#!/usr/bin/env python3
"""Bounded read-only SSH observations for a comma 4. Never copies or writes device files."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import subprocess

SOURCE_COMMIT = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
TINYGRAD_GITLINK = '92b742f711c7d216fd3ed7a46a30a959e3c43bd4'
FIELDS = {
    'model', 'arch', 'agnos_version', 'agnos_marker', 'gpu_char_device',
    'python3_path', 'clang_path', 'clangxx_path', 'capnpc_path', 'scons_path',
    'tinygrad_repo_sha', 'tinygrad_compiler_file', 'data_available_kb',
    'tmp_available_kb', 'mem_available_kb', 'cpu_gpu_thermal_max_mc',
    'cpu_gpu_thermal_count', 'limit_thermal_max_mc', 'limit_thermal_count',
    'scons_candidate_path', 'capnpc_candidate_path', 'scons_module',
    'installed_branch', 'installed_sha',
}
# POSIX sh only. Every remote command reads metadata or files; there is no redirect,
# mkdir, copy, package import, service restart, setting change or build command.
REMOTE = r'''set -u
read_model=''
if [ -r /proc/device-tree/model ]; then read_model=$(tr -d '\000\n' </proc/device-tree/model 2>/dev/null || :); fi
printf 'model=%s\n' "$read_model"
printf 'arch=%s\n' "$(uname -m 2>/dev/null || :)"
printf 'agnos_version=%s\n' "$(cat /VERSION 2>/dev/null || :)"
if [ -e /AGNOS ]; then printf 'agnos_marker=yes\n'; else printf 'agnos_marker=no\n'; fi
if [ -c /dev/kgsl-3d0 ]; then printf 'gpu_char_device=yes\n'; else printf 'gpu_char_device=no\n'; fi
for tool in python3 clang clang++ capnpc scons; do
  case "$tool" in clang++) key=clangxx_path;; *) key="${tool}_path";; esac
  printf '%s=%s\n' "$key" "$(command -v "$tool" 2>/dev/null || :)"
done
for tool in scons capnpc; do
  found=''
  for base in /usr/local/venv/bin /data/openpilot/.venv/bin /data/openpilot/venv/bin /usr/local/bin /usr/bin; do
    if [ -x "$base/$tool" ]; then found="$base/$tool"; break; fi
  done
  printf '%s_candidate_path=%s\n' "$tool" "$found"
done
python_path=$(command -v python3 2>/dev/null || :)
module='unknown'
if [ -n "$python_path" ]; then
  module=$("$python_path" -B -c 'import importlib.util; print("yes" if importlib.util.find_spec("SCons") else "no")' 2>/dev/null || printf 'unknown')
fi
printf 'scons_module=%s\n' "$module"
printf 'tinygrad_repo_sha=%s\n' "$(git -C /data/openpilot/tinygrad_repo rev-parse HEAD 2>/dev/null || :)"
if [ -f /data/openpilot/tinygrad_repo/examples/openpilot/compile_onnx.py ]; then printf 'tinygrad_compiler_file=yes\n'; else printf 'tinygrad_compiler_file=no\n'; fi
printf 'data_available_kb=%s\n' "$(df -Pk /data 2>/dev/null | awk 'NR==2 {print $4}' || :)"
printf 'tmp_available_kb=%s\n' "$(df -Pk /tmp 2>/dev/null | awk 'NR==2 {print $4}' || :)"
printf 'mem_available_kb=%s\n' "$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null || :)"
actual_max=''; actual_count=0; limit_max=''; limit_count=0
for sensor in /sys/class/thermal/thermal_zone*/temp; do
  if [ -r "$sensor" ]; then
    value=$(cat "$sensor" 2>/dev/null || :)
    case "$value" in ''|*[!0-9]*) continue;; esac
    type=$(cat "${sensor%/temp}/type" 2>/dev/null || :)
    case "$type" in
      *lmh*|*limit*|*virtual*)
        limit_count=$((limit_count+1))
        if [ -z "$limit_max" ] || [ "$value" -gt "$limit_max" ]; then limit_max=$value; fi;;
      *cpu*|*CPU*|*gpu*|*GPU*)
        actual_count=$((actual_count+1))
        if [ -z "$actual_max" ] || [ "$value" -gt "$actual_max" ]; then actual_max=$value; fi;;
    esac
  fi
done
printf 'cpu_gpu_thermal_max_mc=%s\ncpu_gpu_thermal_count=%s\nlimit_thermal_max_mc=%s\nlimit_thermal_count=%s\n' "$actual_max" "$actual_count" "$limit_max" "$limit_count"
printf 'installed_branch=%s\n' "$(git -C /data/openpilot branch --show-current 2>/dev/null || :)"
printf 'installed_sha=%s\n' "$(git -C /data/openpilot rev-parse HEAD 2>/dev/null || :)"
'''

def parse_observations(output: str) -> dict[str, str]:
    observations: dict[str, str] = {}
    for line in output.splitlines():
        if len(line) > 512 or '=' not in line:
            raise ValueError('invalid or oversized device response line')
        key, value = line.split('=', 1)
        if key not in FIELDS or key in observations:
            raise ValueError('unexpected or duplicate device response field')
        observations[key] = value
    if set(observations) != FIELDS:
        raise ValueError('incomplete device response')
    if observations['installed_sha'] and not re.fullmatch(r'[0-9a-f]{40}', observations['installed_sha']):
        raise ValueError('invalid installed Git SHA')
    return observations

def classify_failure(stderr: str) -> str:
    if 'No route to host' in stderr:
        return 'NO_ROUTE_TO_HOST'
    if 'timed out' in stderr.lower() or 'Connection timed out' in stderr:
        return 'SSH_TIMEOUT'
    if 'Permission denied' in stderr:
        return 'SSH_AUTH_DENIED'
    if 'Host key verification failed' in stderr:
        return 'HOST_KEY_MISMATCH'
    if 'Operation not permitted' in stderr:
        return 'LOCAL_SOCKET_DENIED'
    return 'SSH_FAILED'

def collect(host: str, timeout_seconds: int = 12) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', host) or host.startswith('-'):
        raise ValueError('host must be a configured SSH alias')
    if not 6 <= timeout_seconds <= 30:
        raise ValueError('timeout must be 6..30 seconds')
    result = {
        'schema_version': 2,
        'observed_at_utc': datetime.now(timezone.utc).isoformat(),
        'host_alias': host,
        'probe_mode': 'READ_ONLY_SSH_NO_DEVICE_WRITES',
        'exact_source_handoff_commit_for_future_isolated_build': SOURCE_COMMIT,
        'expected_pinned_tinygrad_gitlink': TINYGRAD_GITLINK,
        'known_good_confirmed_by_owner': False,
        'qualification_decision': 'NOT_TESTED',
    }
    command = [
        'ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
        '-o', 'NumberOfPasswordPrompts=0', host, 'sh -s',
    ]
    try:
        completed = subprocess.run(command, input=REMOTE, text=True, capture_output=True, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired:
        result.update({'status': 'UNREACHABLE', 'failure_class': 'SSH_TIMEOUT'})
        return result
    if completed.returncode != 0:
        result.update({'status': 'UNREACHABLE', 'failure_class': classify_failure(completed.stderr)})
        return result
    try:
        observations = parse_observations(completed.stdout)
    except ValueError as error:
        result.update({'status': 'INVALID_RESPONSE', 'failure_class': str(error)})
        return result
    result['status'] = 'OBSERVED_READ_ONLY'
    result['observations'] = observations
    # Guardrails for planning only; not OEM ratings or permission to compile.
    holds = []
    if not re.search(r'\bcomma\s*(?:4|four|mici)\b', observations['model'].casefold()):
        holds.append('device model does not identify comma 4')
    for key, required in (('arch', 'aarch64'), ('agnos_marker', 'yes'), ('gpu_char_device', 'yes')):
        if observations[key] != required:
            holds.append(f'{key} differs from {required}')
    version = observations['agnos_version']
    result['agnos_compatibility'] = ('OBSERVED_COMPATIBILITY_PENDING' if version in ('19.9', '19.8.1')
                                     else 'UNRECOGNIZED_VERSION_HOLD')
    result['build_target_match'] = 'BUILD_TARGET_MISMATCH' if version == '19.9' else ('HISTORICAL_REFERENCE_ONLY' if version == '19.8.1' else 'UNKNOWN')
    if version not in ('19.9', '19.8.1'):
        holds.append('AGNOS version unrecognized for this campaign')
    # This is only a fixed-copy floor. Cache, output, tooling and working-set
    # budgets must be measured before any device-side build can be approved.
    fixed_copy_kb = (223006720 + 219518275 + 1023) // 1024
    reserve_kb = 2 * 1024 * 1024
    result['storage_plan'] = {
        'fixed_archive_and_extracted_source_kb': fixed_copy_kb,
        'minimum_reserve_kb': reserve_kb,
        'cache_output_tooling_tmp_budget_kb': None,
        'status': 'REQUIRED_CAPACITY_UNKNOWN',
    }
    result['tmpdir_plan'] = ('ISOLATED_DATA_TMPDIR_REQUIRED_IF_CAPACITY_PROVEN'
                             if observations['tmp_available_kb'].isdigit() and int(observations['tmp_available_kb']) < 1024 * 1024
                             else 'MEASURE_TMP_WORKING_SET_BEFORE_BUILD')
    for key, floor in (('data_available_kb', fixed_copy_kb + reserve_kb), ('mem_available_kb', 1024 * 1024)):
        value = observations[key]
        if not value.isdigit() or int(value) < floor:
            holds.append(f'{key} below measured fixed-copy/reserve floor or unavailable')
    thermal = observations['cpu_gpu_thermal_max_mc']
    if not thermal.isdigit() or int(thermal) >= 70000 or not observations['cpu_gpu_thermal_count'].isdigit() or int(observations['cpu_gpu_thermal_count']) == 0:
        holds.append('CPU/GPU thermal reading unavailable or at/above 70 C planning stop')
    for key in ('python3_path', 'clang_path', 'clangxx_path'):
        if not observations[key]:
            holds.append(f'{key} unavailable in observed PATH')
    for tool in ('capnpc', 'scons'):
        if not observations[f'{tool}_path'] and not observations[f'{tool}_candidate_path'] and not (tool == 'scons' and observations['scons_module'] == 'yes'):
            holds.append(f'{tool} unresolved in PATH and bounded candidate locations')
    if observations['tinygrad_repo_sha'] != TINYGRAD_GITLINK or observations['tinygrad_compiler_file'] != 'yes':
        holds.append('observed tinygrad compiler does not match pinned Git link')
    if not observations['installed_sha'] or not observations['installed_branch']:
        holds.append('installed branch/SHA unavailable; owner confirmation pending')
    result['planning_holds'] = holds
    result['read_only_prerequisites'] = 'OBSERVED_WITH_HOLDS' if holds else 'OBSERVED_COMPATIBILITY_PENDING'
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='comma', help='configured SSH alias; default: comma')
    parser.add_argument('--timeout-seconds', type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(collect(args.host, args.timeout_seconds), indent=2, sort_keys=True))
