#!/usr/bin/env python3
"""Recovery and exclusive-worktree guard for the offline engineering campaign."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN = Path(__file__).resolve().parent
STATE = CAMPAIGN / 'CAMPAIGN_STATE.json'
LOCK = CAMPAIGN / '.campaign.lock'


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
    return {'actual_head': head, 'recorded_head': recorded, 'branch': branch, 'recorded_branch': state['active_engineering']['branch'], 'checkpoint_commit': checkpoint_commit, 'pending_operation': pending, 'dirty_paths': status, 'problems': problems, 'release_status': state['release_qualification']['status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    recover = subs.add_parser('recover')
    recover.add_argument('--state-file', type=Path, default=STATE)
    locked = subs.add_parser('locked-run')
    locked.add_argument('command_to_run', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == 'recover':
        result = inspect(args.state_file)
        print(json.dumps(result, indent=2))
        return 2 if result['problems'] else 0
    if not args.command_to_run:
        parser.error('locked-run requires a command after --')
    command = args.command_to_run[1:] if args.command_to_run[0] == '--' else args.command_to_run
    with LOCK.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('campaign worktree is owned by another active process', file=sys.stderr)
            return 3
        lock.seek(0)
        lock.truncate()
        lock.write(json.dumps({'pid': os.getpid(), 'command': command}) + '\n')
        lock.flush()
        try:
            return subprocess.call(command, cwd=ROOT)
        finally:
            lock.seek(0)
            lock.truncate()
            lock.flush()


if __name__ == '__main__':
    sys.exit(main())
