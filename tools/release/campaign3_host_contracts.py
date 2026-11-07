#!/usr/bin/env python3
"""Execution-free host contracts. Inputs never establish device qualification."""
from __future__ import annotations

from pathlib import Path
import re
import stat

from tools.release.campaign3_offline import WRITE_AREAS, SERVICES, replay_state


def _mount_id(path: Path) -> str:
    """Return the covering mount ID, including bind mounts on the same device."""
    target = str(path)
    winner = (-1, '')
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = line.split()
        mount = fields[4].replace('\\040', ' ')
        if target == mount or target.startswith(mount.rstrip('/') + '/'):
            if len(mount) > winner[0]:
                winner = (len(mount), fields[0])
    if not winner[1]:
        raise ValueError('no covering mount')
    return winner[1]


def validate_write_coverage(root: Path, paths: dict[str, Path]) -> dict:
    """Check actual direct children and mount identity; never assert a hard quota."""
    if not isinstance(paths, dict) or set(paths) != set(WRITE_AREAS):
        raise ValueError('six exact write areas required')
    root = Path(root)
    if not root.is_absolute() or '..' in root.parts or \
            not re.fullmatch(r'pilot-[0-9a-f]{16}', root.name) or root.resolve() != root:
        raise ValueError('invalid run root')
    root_stat = root.lstat()
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
        raise ValueError('run root is not a real directory')
    mount = _mount_id(root)
    checked = {}
    for area in WRITE_AREAS:
        path = Path(paths[area])
        if path != root / area or '..' in path.parts:
            raise ValueError(f'{area}: path is not the exact direct child')
        entry = path.lstat()
        if not stat.S_ISDIR(entry.st_mode) or stat.S_ISLNK(entry.st_mode) or path.resolve() != path:
            raise ValueError(f'{area}: symlink or non-directory')
        if entry.st_dev != root_stat.st_dev or _mount_id(path) != mount:
            raise ValueError(f'{area}: crosses filesystem or mount')
        checked[area] = {'device': entry.st_dev, 'mount_id': mount, 'inode': entry.st_ino}
    return {'coverage': 'SIX_AREAS_ONE_ACTUAL_MOUNT', 'root_mount_id': mount,
            'paths': checked, 'hard_limit_proven': False, 'device_qualified': False}


def supervisor_trace(events: list[dict], *, scope: str, deadline_seconds: float = 4.9) -> dict:
    """Check a finite synthetic failure trace, without signaling any process."""
    reasons = []
    if not scope.startswith('campaign3-') or not 0 < deadline_seconds < 5.0:
        return {'decision': 'NO_GO', 'reasons': ['INVALID_SCOPE_OR_DEADLINE'], 'device_qualified': False}
    if not isinstance(events, list) or len(events) > 8:
        return {'decision': 'NO_GO', 'reasons': ['INVALID_TRACE'], 'device_qualified': False}
    times = []
    for item in events:
        if not isinstance(item, dict) or set(item) != {'at', 'kind', 'scope'} or item['scope'] != scope or \
                type(item['at']) not in (int, float) or not 0 <= item['at'] < 60:
            reasons.append('INVALID_EVENT'); continue
        times.append(item['at'])
    if times != sorted(times) or len(times) != len(events):
        reasons.append('NONMONOTONIC_TRACE')
    kinds = [item.get('kind') for item in events if isinstance(item, dict)]
    failures = [i for i, kind in enumerate(kinds) if kind in ('guardian_sigkill', 'supervisor_disconnect')]
    if len(failures) != 1:
        reasons.append('ONE_FAILURE_REQUIRED')
    elif not reasons:
        index = failures[0]
        if kinds[index+1:] != ['abort', 'scope_empty'] or events[-1]['at'] - events[index]['at'] > deadline_seconds:
            reasons.append('BOUNDED_ABORT_AND_EMPTY_SCOPE_REQUIRED')
    return {'decision': 'SYNTHETIC_CONTRACT_PASS_DEVICE_HOLD' if not reasons else 'NO_GO',
            'reasons': reasons, 'device_qualified': False}


def acquisition_contract(frames: list[dict], evidence: list[dict], *, run_id: str,
                         observer_id: str, verify_provenance) -> dict:
    """Require an external verifier and fresh per-feed acquisition over 30 seconds.

    The caller's verifier is a separate trust boundary. A test stub or self-declared
    field cannot authenticate cereal, device identity, or parked state.
    """
    reasons = []
    if not run_id or not observer_id or len(evidence) != len(frames):
        reasons.append('PROVENANCE_CONTEXT_MISSING')
    previous = {name: None for name in SERVICES}
    sources = {name: None for name in SERVICES}
    times = []
    for frame, record in zip(frames, evidence):
        if not isinstance(record, dict) or set(record) != {'run_id', 'observer_id', 'acquired_at', 'feeds'} or \
                record['run_id'] != run_id or record['observer_id'] != observer_id or \
                type(record['acquired_at']) not in (int, float) or \
                not isinstance(record['feeds'], dict) or set(record['feeds']) != set(SERVICES):
            reasons.append('PROVENANCE_CONTEXT_INVALID'); continue
        acquired = record['acquired_at']
        if not 0 <= acquired < float('inf') or not isinstance(frame, dict) or \
                type(frame.get('at')) not in (int, float) or not 0 <= acquired - frame['at'] <= 1.0:
            reasons.append('ACQUISITION_STALE'); continue
        times.append(acquired)
        for service in SERVICES:
            feed = record['feeds'][service]
            if not isinstance(feed, dict) or set(feed) != {'source_id', 'sequence', 'proof'} or \
                    not isinstance(feed['source_id'], str) or not feed['source_id'] or \
                    type(feed['sequence']) is not int or feed['sequence'] < 0 or \
                    previous[service] is not None and feed['sequence'] <= previous[service] or \
                    sources[service] is not None and feed['source_id'] != sources[service]:
                reasons.append('FEED_PROVENANCE_INVALID'); continue
            previous[service] = feed['sequence']
            sources[service] = feed['source_id']
            try:
                if verify_provenance(run_id, observer_id, service, frame, record, feed) is not True:
                    reasons.append('PROVENANCE_UNAUTHENTICATED')
            except Exception:
                reasons.append('PROVENANCE_UNAUTHENTICATED')
    if len(times) < 31 or times != sorted(set(times)) or times[-1] - times[0] < 30 or \
            any(b-a > 1 for a, b in zip(times, times[1:])):
        reasons.append('FRESH_30_SECOND_ACQUISITION_MISSING')
    if None not in sources.values() and len(set(sources.values())) != len(SERVICES):
        reasons.append('FEED_SOURCES_NOT_DISTINCT')
    replay = replay_state(frames)
    if replay['decision'] != 'SYNTHETIC_POLICY_PASS_DEVICE_HOLD':
        reasons.extend(replay['reasons'])
    return {'decision': 'MONITOR_CONTRACT_PASS_DEVICE_HOLD' if not reasons else 'NO_GO',
            'reasons': sorted(set(reasons)), 'device_qualified': False,
            'authenticated_live_device_proof': False}
