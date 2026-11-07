#!/usr/bin/env python3
"""Fail-closed assessment of read-only Campaign 2 device observations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
INSTALLED = 'a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1'


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate evidence key: {key}')
        result[key] = value
    return result


def row(name: str, status: str, evidence: str, requirement: str) -> dict:
    return {'requirement': name, 'status': status, 'evidence': evidence,
            'next_proof': requirement}


def assess(observation: dict) -> dict:
    if observation.get('schema_version') != 1 or observation.get('scope', '').find('read-only') < 0:
        raise ValueError('not a read-only device observation')
    fields = observation.get('fields')
    if not isinstance(fields, dict):
        raise ValueError('device fields missing')
    mount = fields.get('data_mount', '')
    ext4 = bool(re.search(r'\s- ext4\s', mount))
    features = fields.get('data_ext4_features', '').split()
    project = 'project' in features
    mount_project = bool(re.search(r'\b(prjquota|pquota)\b', mount))
    thermal = fields.get('thermals', [])
    if not isinstance(thermal, list):
        thermal = []
    cpu_sensor = any(re.match(r'cpu[^|]*\|[0-9]+\|/sys/class/thermal/', x) for x in thermal if isinstance(x, str))
    gpu_sensor = any(re.match(r'gpu[01][^|]*\|[0-9]+\|/sys/class/thermal/', x) for x in thermal if isinstance(x, str))
    data_free = fields.get('data_free_kib', '')
    free_observed = isinstance(data_free, str) and data_free.isdecimal() and int(data_free) > 2*1024**2
    identity = (fields.get('model') == 'comma mici' and fields.get('arch') == 'aarch64' and
                fields.get('agnos') == '19.9' and fields.get('installed_sha') == INSTALLED and
                fields.get('installed_branch') == 'sp-honda-dev-202608')
    rows = [
        row('device_and_known_good_identity', 'PASS' if identity else 'FAIL',
            'read-only model, architecture, AGNOS and installed Git identity',
            'Recheck exact installed branch/SHA before any later action'),
        row('data_filesystem_identity', 'PASS' if ext4 else 'UNKNOWN',
            mount or 'mount observation missing', 'Verify /data mount source and filesystem on device'),
        row('ext4_project_quota_capability', 'FAIL' if ext4 and (not project or not mount_project) else 'UNKNOWN',
            f'project_feature={project}; project_mount_option={mount_project}',
            'Current filesystem lacks observed project quota prerequisites; do not alter it in Campaign 2'),
        row('aggregate_hard_storage_limit', 'UNKNOWN',
            'No isolated enforcement test; read-only inspection cannot demonstrate a hard bound',
            'Separately authorize and prove an isolated aggregate limit including all compiler writes'),
        row('disk_reserve_under_compilation', 'UNKNOWN' if free_observed else 'FAIL',
            f'last_snapshot_free_kib={data_free or "missing"}; actual compiler peak unknown',
            'Measure peak usage under hard quota; keep at least 2 GiB free, preferably 4 GiB'),
        row('cgroup_memory_controller', 'PASS' if fields.get('cgroup_type') == 'cgroup2fs' and
            'memory' in fields.get('cgroup_controllers', '').split() else 'UNKNOWN',
            'read-only cgroup v2 controller observation',
            'Test workload memory.max, OOM events and process termination in separate authorized scope'),
        row('gpu_memory_containment', 'UNKNOWN',
            'KGSL node does not prove GPU allocation accounting or containment',
            'Obtain bounded actual GPU allocation and driver error evidence'),
        row('cpu_gpu_thermal_paths', 'PASS' if cpu_sensor and gpu_sensor else 'UNKNOWN',
            'actual CPU/GPU thermal paths observed, no sustained workload',
            'Validate sensor semantics and continuous response under authorized isolated load'),
        row('continuous_parked_disengaged_state', 'UNKNOWN',
            'No authenticated 30-second concurrent pandaStates/carState/controlsState proof',
            'Establish independent live stationary or physically controlled disconnected bench proof'),
        row('independent_abort_and_cleanup', 'UNKNOWN',
            'Host fixture only; device controller and cleanup not executed',
            'Hardware-test guardian, process ownership, failure recovery and cleanup boundaries'),
    ]
    return {'schema_version': 1, 'source_commit': SOURCE,
            'decision': 'B2_HARDWARE_NOT_QUALIFIED', 'device_writes': False,
            'rows': rows, 'qcom_compilation': 'NOT_EXECUTED'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('observation', type=Path)
    args = parser.parse_args()
    if not args.observation.is_file() or args.observation.is_symlink() or args.observation.stat().st_size > 256*1024:
        parser.error('missing, symlinked or oversized observation')
    report = assess(json.loads(args.observation.read_text(), object_pairs_hook=unique_pairs))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__': raise SystemExit(main())
