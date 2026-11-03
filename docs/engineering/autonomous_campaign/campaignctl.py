#!/usr/bin/env python3
"""Recovery and exclusive-worktree guard for the offline engineering campaign."""
import argparse
import fcntl
import json
import os
import secrets
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN = Path(__file__).resolve().parent
STATE = CAMPAIGN / 'CAMPAIGN_STATE.json'
LOCK = Path(os.environ.get('CAMPAIGN_LOCK_FILE', CAMPAIGN / '.campaign.lock'))
LEASE = Path(os.environ.get('CAMPAIGN_LEASE_DIR', CAMPAIGN / '.campaign.lease'))


def git(*args):
    return subprocess.run(['git', '-c', 'filter.lfs.process=', '-c', 'filter.lfs.required=false', *args], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def inspect(state_path=STATE):
    state = json.loads(Path(state_path).read_text())
    head = git('rev-parse', 'HEAD')
    branch = git('branch', '--show-current') or None
    status = git('status', '--porcelain=v1').splitlines()
    recorded = state['active_engineering']['head']
    pending = state.get('operation_in_progress')
    match = head == recorded
    checkpoint_commit = False
    if not match:
        parent = git('rev-parse', 'HEAD^') if git('rev-list', '--count', 'HEAD') != '1' else None
        if parent == recorded:
            changed = git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').splitlines()
            checkpoint_commit = bool(changed) and all(p.startswith('docs/engineering/autonomous_campaign/') for p in changed)
    problems = []
    if branch != state['active_engineering']['branch']:
        problems.append('branch differs from recorded branch')
    if not (match or checkpoint_commit):
        problems.append('HEAD differs from recorded checkpoint')
    if pending:
        problems.append('operation was interrupted or remains in progress')
    if status:
        problems.append('worktree has uncommitted changes')
    lease = None
    if LEASE.exists():
        owner = LEASE / 'owner.json'
        lease = {'status': 'active'} if owner.exists() else {'status': 'incomplete_claim'}
        problems.append('campaign run lease is active; reconcile ownership before a new run')
    return {'run_lease': lease, 'actual_head': head, 'recorded_head': recorded, 'branch': branch, 'recorded_branch': state['active_engineering']['branch'], 'checkpoint_commit': checkpoint_commit, 'pending_operation': pending, 'dirty_paths': status, 'problems': problems, 'release_status': state['release_qualification']['status']}


def _read_owner() -> dict:
    return json.loads((LEASE / 'owner.json').read_text())


def _write_owner(owner: dict) -> None:
    temporary = LEASE / 'owner.json.tmp'
    temporary.write_text(json.dumps(owner) + '\n')
    temporary.replace(LEASE / 'owner.json')


def _stale() -> bool:
    try:
        last = _read_owner()['heartbeat_epoch']
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        last = LEASE.stat().st_mtime
    ttl = int(os.environ.get('CAMPAIGN_LEASE_TTL_SECONDS', '5400'))
    return time.time() - last > ttl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    recover = subs.add_parser('recover')
    recover.add_argument('--state-file', type=Path, default=STATE)
    claim = subs.add_parser('claim-run')
    claim.add_argument('--reclaim-stale', action='store_true')
    finish = subs.add_parser('finish-run')
    finish.add_argument('token')
    heartbeat = subs.add_parser('heartbeat')
    heartbeat.add_argument('token')
    locked = subs.add_parser('locked-run')
    locked.add_argument('--token', required=True)
    locked.add_argument('command_to_run', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == 'recover':
        result = inspect(args.state_file)
        print(json.dumps(result, indent=2))
        return 2 if result['problems'] else 0
    # All lease changes and modifying commands use the same OS lock. A stale
    # owner cannot race an active command or continue after token replacement.
    with LOCK.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('campaign worktree is owned by another active process', file=sys.stderr)
            return 3
        if args.command == 'claim-run':
            if LEASE.exists():
                if not args.reclaim_stale or not _stale():
                    print('campaign run lease already active or not yet stale', file=sys.stderr)
                    return 3
                for name in ('owner.json.tmp', 'owner.json'):
                    (LEASE / name).unlink(missing_ok=True)
                LEASE.rmdir()
            LEASE.mkdir()
            token = secrets.token_hex(16)
            _write_owner({'token': token, 'heartbeat_epoch': time.time()})
            print(token)
            return 0
        try:
            owner = _read_owner()
        except (FileNotFoundError, json.JSONDecodeError):
            print('campaign run lease missing or incomplete', file=sys.stderr)
            return 3
        if not secrets.compare_digest(args.token, owner['token']):
            print('campaign run lease token mismatch', file=sys.stderr)
            return 3
        if args.command == 'finish-run':
            (LEASE / 'owner.json').unlink()
            LEASE.rmdir()
            return 0
        owner['heartbeat_epoch'] = time.time()
        _write_owner(owner)
        if args.command == 'heartbeat':
            return 0
        if not args.command_to_run:
            parser.error('locked-run requires a command after --')
        command = args.command_to_run[1:] if args.command_to_run[0] == '--' else args.command_to_run
        lock.seek(0)
        lock.truncate()
        lock.write(json.dumps({'pid': os.getpid(), 'command': command}) + '\n')
        lock.flush()
        try:
            return subprocess.call(command, cwd=ROOT)
        finally:
            owner['heartbeat_epoch'] = time.time()
            _write_owner(owner)
            lock.seek(0)
            lock.truncate()
            lock.flush()


if __name__ == '__main__':
    sys.exit(main())
