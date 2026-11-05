#!/usr/bin/env python3
"""Offline, read-only source preflight. This does not produce a release package."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


DENIED_PREFIXES = (
  'panda/', 'opendbc_repo/', 'openpilot/selfdrive/car/',
  'openpilot/selfdrive/controls/', 'openpilot/selfdrive/pandad/',
  'openpilot/system/manager/',
)
LFS_PREFIX = b'version https://git-lfs.github.com/spec/v1\n'


def git(repo, *args, binary=False):
  # Disable Git LFS clean filters: status must not write to the shared LFS store.
  command = ['git', '-c', 'filter.lfs.process=', '-c', 'filter.lfs.clean=cat',
             '-c', 'filter.lfs.smudge=cat', '-c', 'filter.lfs.required=false',
             '-C', str(repo), *args]
  result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  return result.stdout if binary else result.stdout.decode().strip()


def inspect(repo, commit, baseline, max_blob_bytes):
  root = Path(git(repo, 'rev-parse', '--show-toplevel')).resolve()
  head = git(root, 'rev-parse', 'HEAD')
  source = git(root, 'rev-parse', '--verify', f'{commit}^{{commit}}')
  issues = []
  if source != head:
    issues.append('requested commit is not worktree HEAD')

  dirty = git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=all').splitlines()
  if dirty:
    issues.append('root worktree has modified or untracked files')

  entries = []
  for record in git(root, 'ls-tree', '-rlz', '--full-tree', source, binary=True).split(b'\0'):
    if not record:
      continue
    metadata, raw_path = record.split(b'\t', 1)
    mode, kind, oid, size = metadata.decode().split()
    entries.append((mode, kind, oid, raw_path.decode('utf-8', 'surrogateescape'), size))

  blobs = [(oid, path) for mode, kind, oid, path, size in entries if kind == 'blob']
  sizes = {path: int(size) for mode, kind, oid, path, size in entries if kind == 'blob'}
  oversized = [{'path': path, 'bytes': size} for path, size in sorted(sizes.items()) if size > max_blob_bytes]
  if oversized:
    issues.append('committed Git blob exceeds size limit')

  submodules = []
  for mode, kind, oid, path, size in entries:
    if mode != '160000':
      continue
    checkout = root / path
    actual = None
    state = 'missing'
    # Empty gitlink directories otherwise resolve to the parent repository.
    if checkout.is_dir() and (checkout / '.git').exists():
      try:
        actual = git(checkout, 'rev-parse', 'HEAD')
        state = 'pinned' if actual == oid else 'wrong_commit'
        if git(checkout, 'status', '--porcelain=v1', '--untracked-files=all'):
          state = 'dirty' if state == 'pinned' else state
      except subprocess.CalledProcessError:
        pass
    if state != 'pinned':
      issues.append(f'submodule {path}: {state}')
    submodules.append({'path': path, 'pinned': oid, 'actual': actual, 'state': state})

  # The selector intentionally excludes the optional large model. Check only
  # assets that would enter this release, while retaining all pointer states.
  selector = root / 'tools/release/release_files.py'
  selected = []
  if selector.is_file():
    result = subprocess.run([sys.executable, str(selector)], cwd=root, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selected = [p.decode('utf-8', 'surrogateescape') for p in result.stdout.split(b'\0') if p]
    for item in submodules:
      if item['path'] in selected:
        issues.append(f'release selector includes unexpanded gitlink {item["path"]}')
  else:
    issues.append('MVL release_files.py selector missing')
  selected_set = set(selected)

  lfs = []
  for oid, path in blobs:
    if sizes[path] > 1024:
      continue
    blob = git(root, 'cat-file', 'blob', oid, binary=True)
    if not blob.startswith(LFS_PREFIX):
      continue
    pointer = dict(line.split(' ', 1) for line in blob.decode().splitlines() if ' ' in line)
    expected = pointer.get('oid', '').removeprefix('sha256:')
    checkout = root / path
    actual = hashlib.sha256(checkout.read_bytes()).hexdigest() if checkout.is_file() else None
    state = 'hydrated' if actual == expected else 'pointer_or_mismatch'
    if path in selected_set and state != 'hydrated':
      issues.append(f'LFS asset {path}: {state}')
    lfs.append({'path': path, 'sha256': expected, 'state': state,
                'release_selected': path in selected_set})

  changed = []
  denied = []
  if baseline:
    base = git(root, 'rev-parse', '--verify', f'{baseline}^{{commit}}')
    if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base, source],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
      issues.append('baseline is not an ancestor of source commit')
    changed = [p.decode('utf-8', 'surrogateescape') for p in git(root, 'diff', '--name-only', '-z', base, source, binary=True).split(b'\0') if p]
    denied = [path for path in changed if path.startswith(DENIED_PREFIXES)]
    if denied:
      issues.append('restricted control/Panda/manager source changed')

  return {
    'result': 'PASS' if not issues else 'HOLD', 'head': head, 'source_commit': source,
    'source_tree': git(root, 'rev-parse', f'{source}^{{tree}}'),
    'baseline': baseline, 'root': str(root), 'issues': sorted(set(issues)),
    'dirty_paths': dirty, 'blob_count': len(blobs), 'max_blob_bytes': max_blob_bytes,
    'oversized_blobs': oversized, 'submodules': submodules, 'lfs_assets': lfs,
    'changed_paths': changed, 'restricted_changes': denied,
    'release_selector_path_count': len(selected),
    'scope': 'read-only source preflight; no build, package, device, or release approval',
  }


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--repo', type=Path, default=Path.cwd())
  parser.add_argument('--commit', default='HEAD')
  parser.add_argument('--baseline', help='compare source boundary with this exact commit')
  parser.add_argument('--max-blob-bytes', type=int, default=95 * 1024 * 1024)
  args = parser.parse_args()
  if args.max_blob_bytes < 1:
    parser.error('--max-blob-bytes must be positive')
  try:
    report = inspect(args.repo, args.commit, args.baseline, args.max_blob_bytes)
  except (OSError, ValueError, subprocess.CalledProcessError) as exc:
    print(json.dumps({'result': 'ERROR', 'error': str(exc)}, sort_keys=True))
    return 2
  print(json.dumps(report, indent=2, sort_keys=True))
  return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
  raise SystemExit(main())
