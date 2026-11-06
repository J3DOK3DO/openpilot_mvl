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
    'tmp_available_kb', 'mem_available_kb', 'thermal_max_mc', 'thermal_count',
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
printf 'tinygrad_repo_sha=%s\n' "$(git -C /data/openpilot/tinygrad_repo rev-parse HEAD 2>/dev/null || :)"
if [ -f /data/openpilot/tinygrad_repo/examples/openpilot/compile_onnx.py ]; then printf 'tinygrad_compiler_file=yes\n'; else printf 'tinygrad_compiler_file=no\n'; fi
printf 'data_available_kb=%s\n' "$(df -Pk /data 2>/dev/null | awk 'NR==2 {print $4}' || :)"
printf 'tmp_available_kb=%s\n' "$(df -Pk /tmp 2>/dev/null | awk 'NR==2 {print $4}' || :)"
printf 'mem_available_kb=%s\n' "$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null || :)"
max=''; count=0
for sensor in /sys/class/thermal/thermal_zone*/temp; do
  if [ -r "$sensor" ]; then
    value=$(cat "$sensor" 2>/dev/null || :)
    case "$value" in ''|*[!0-9]*) continue;; esac
    count=$((count+1))
    if [ -z "$max" ] || [ "$value" -gt "$max" ]; then max=$value; fi
  fi
done
printf 'thermal_max_mc=%s\nthermal_count=%s\n' "$max" "$count"
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
        'schema_version': 1,
        'observed_at_utc': datetime.now(timezone.utc).isoformat(),
        'host_alias': host,
        'probe_mode': 'READ_ONLY_SSH_NO_DEVICE_WRITES',
        'expected_source_commit_for_future_isolated_build': SOURCE_COMMIT,
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
    for key, required in (('arch', 'aarch64'), ('agnos_version', '19.8.1'), ('agnos_marker', 'yes'), ('gpu_char_device', 'yes')):
        if observations[key] != required:
            holds.append(f'{key} differs from {required}')
    for key, floor in (('data_available_kb', 12 * 1024 * 1024), ('mem_available_kb', 2 * 1024 * 1024)):
        value = observations[key]
        if not value.isdigit() or int(value) < floor:
            holds.append(f'{key} below planning guardrail or unavailable')
    thermal = observations['thermal_max_mc']
    if not thermal.isdigit() or int(thermal) >= 70000:
        holds.append('thermal headroom unavailable or at/above planning guardrail')
    for key in ('python3_path', 'clang_path', 'clangxx_path', 'capnpc_path'):
        if not observations[key]:
            holds.append(f'{key} unavailable in observed PATH')
    if not observations['installed_sha'] or not observations['installed_branch']:
        holds.append('installed branch/SHA unavailable; owner confirmation pending')
    result['planning_holds'] = holds
    result['read_only_prerequisites'] = 'OBSERVED_WITH_HOLDS' if holds else 'OBSERVED_ONLY_OWNER_AND_BUILD_AUTHORIZATION_STILL_REQUIRED'
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='comma', help='configured SSH alias; default: comma')
    parser.add_argument('--timeout-seconds', type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(collect(args.host, args.timeout_seconds), indent=2, sort_keys=True))
