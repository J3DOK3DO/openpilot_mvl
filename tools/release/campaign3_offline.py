#!/usr/bin/env python3
"""Offline feasibility and synthetic state replay. No device adapter or executor."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'

GIB = 1024 ** 3
SERVICES = ('pandaStates', 'carState', 'controlsState')
WRITE_AREAS = ('source', 'cache', 'home', 'tmp', 'outputs', 'diagnostics')


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _path(value):
    if not isinstance(value, str) or not value.startswith('/') or '\x00' in value:
        raise ValueError('invalid absolute path')
    path = Path(value)
    if '..' in path.parts or str(path) != value.rstrip('/'):
        raise ValueError('noncanonical or traversing path')
    return path


def storage_assessment(spec: dict) -> dict:
    """Assess a proposed one-run boundary from evidence, never certify enforcement."""
    if not isinstance(spec, dict):
        raise ValueError('storage spec must be an object')
    root = _path(spec.get('run_root'))
    if not re.fullmatch(r'pilot-[0-9a-f]{16}', root.name) or root.parent not in (
            Path('/tmp'), Path('/data/mvl-builds') / SOURCE):
        raise ValueError('run root must be an exact isolated pilot path')
    paths = spec.get('write_paths')
    if not isinstance(paths, dict) or set(paths) != set(WRITE_AREAS):
        raise ValueError('all six write areas required')
    parsed = {name: _path(value) for name, value in paths.items()}
    if any(path == root or not path.is_relative_to(root) for path in parsed.values()) or len(set(parsed.values())) != len(parsed):
        raise ValueError('write paths must be distinct descendants of one run root')
    for name, path in parsed.items():
        if path != root / name:
            raise ValueError('each write path must be a direct named child')
    free = spec.get('free_bytes')
    bound = spec.get('hard_limit_bytes')
    source = spec.get('measured_source_bytes')
    if any(type(x) is not int or x <= 0 for x in (free, bound, source)):
        raise ValueError('positive integer capacities required')
    method = spec.get('method')
    if method not in ('ext4_project_quota', 'xfs_project_quota', 'bounded_filesystem'):
        raise ValueError('no supported aggregate boundary mechanism')
    evidence = spec.get('capability', {})
    if not isinstance(evidence, dict):
        raise ValueError('capability evidence must be an object')
    required = ('active_feature', 'active_mount', 'isolated_run', 'all_writes_confined',
                'hard_enospc_tested', 'no_external_writes', 'cleanup_provenance_verified')
    missing = [key for key in required if evidence.get(key) is not True]
    if method == 'ext4_project_quota' and evidence.get('observed_data_ext4_project_feature') is not True:
        missing.append('observed_data_ext4_project_feature')
    if spec.get('observed_filesystem') == 'ext4' and method == 'xfs_project_quota':
        missing.append('filesystem_method_mismatch')
    if bound <= source:
        missing.append('source_exceeds_or_equals_limit')
    if free - bound < 2 * GIB:
        missing.append('two_gib_reserve_not_proven')
    return {'decision': 'OFFLINE_CANDIDATE_ONLY' if not missing else 'NO_GO',
            'missing': missing, 'reserve_after_full_allocation_bytes': free - bound,
            'preferred_four_gib_reserve': free - bound >= 4 * GIB,
            'aggregate_hard_limit_enforced': False, 'device_qualified': False,
            'quota_changed': False}


def containment_assessment(spec: dict) -> dict:
    """Require an independent owner of the entire worker cgroup, not a PGID."""
    if not isinstance(spec, dict):
        raise ValueError('containment spec must be an object')
    required = ('independent_supervisor', 'supervisor_survives_guardian_sigkill',
                'worker_cgroup_owned', 'all_descendants_confined', 'cgroup_kill_available',
                'guardian_liveness_observed', 'supervisor_liveness_observed',
                'bounded_kill_verified', 'empty_cgroup_verified', 'cleanup_owned_and_verified')
    missing = [key for key in required if spec.get(key) is not True]
    if spec.get('mechanism') != 'independent_cgroup_v2':
        missing.append('independent_cgroup_v2_required')
    return {'decision': 'OFFLINE_DESIGN_COMPLETE_DEVICE_HOLD' if not missing else 'NO_GO',
            'missing': missing, 'host_fixture_proof': False, 'device_qualified': False}


def replay_state(frames: list[dict]) -> dict:
    """Require continuous coherent updates from three independent synthetic feeds."""
    reasons = set()
    if not isinstance(frames, list) or len(frames) < 31:
        return {'decision': 'NO_GO', 'reasons': ['INSUFFICIENT_FRAMES']}
    previous = None
    first = None
    for frame in frames:
        if not isinstance(frame, dict) or set(frame) != {'at', *SERVICES} or not _number(frame['at']):
            reasons.add('PARSE_OR_UNKNOWN_STATE'); continue
        at = frame['at']
        if first is None: first = at
        if previous is not None and not 0 < at - previous <= 1.0:
            reasons.add('GAP_OR_NONMONOTONIC')
        previous = at
        stamps = []
        for service in SERVICES:
            value = frame[service]
            if not isinstance(value, dict) or set(value) != {'timestamp', 'alive', 'valid', 'value'}:
                reasons.add('PARSE_OR_UNKNOWN_STATE'); continue
            stamp = value['timestamp']
            if not _number(stamp) or not 0 <= at - stamp <= 1.0 or value['alive'] is not True or value['valid'] is not True:
                reasons.add('STALE_OR_MISSING_SERVICE'); continue
            stamps.append(stamp)
            data = value['value']
            if not isinstance(data, dict):
                reasons.add('PARSE_OR_UNKNOWN_STATE'); continue
            if service == 'pandaStates':
                if set(data) != {'ignitionCan', 'ignitionLine'} or data['ignitionCan'] is not False or data['ignitionLine'] is not False:
                    reasons.add('IGNITION_OR_UNKNOWN')
            elif service == 'carState':
                if set(data) != {'vEgo'} or not _number(data['vEgo']) or not 0 <= data['vEgo'] <= 0.01:
                    reasons.add('MOTION_OR_UNKNOWN')
            elif set(data) != {'enabled'} or data['enabled'] is not False:
                reasons.add('ENGAGED_OR_UNKNOWN')
        if len(stamps) == 3 and max(stamps) - min(stamps) > 0.25:
            reasons.add('TIMESTAMP_SKEW')
    if first is None or previous is None or previous - first < 30:
        reasons.add('DURATION_SHORT')
    return {'decision': 'SYNTHETIC_POLICY_PASS_DEVICE_HOLD' if not reasons else 'NO_GO',
            'reasons': sorted(reasons), 'device_qualified': False}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('duplicate key')
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('storage', 'containment', 'state'))
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    if args.input.is_symlink() or not args.input.is_file() or args.input.stat().st_size > 1024 * 1024:
        parser.error('input must be a regular file of at most 1 MiB')
    try:
        data = json.loads(args.input.read_text(), object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite number')))
        report = {'storage': storage_assessment, 'containment': containment_assessment,
                  'state': replay_state}[args.kind](data)
    except (ValueError, TypeError, KeyError) as exc:
        report = {'decision': 'NO_GO', 'reasons': ['INVALID_INPUT', str(exc)]}
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report['decision'] in ('OFFLINE_CANDIDATE_ONLY', 'OFFLINE_DESIGN_COMPLETE_DEVICE_HOLD',
                                      'SYNTHETIC_POLICY_PASS_DEVICE_HOLD') else 2


if __name__ == '__main__':
    raise SystemExit(main())
