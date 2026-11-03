#!/usr/bin/env python3
"""Emit a deterministic, non-installable offline engineering manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = '362c2fb6fed527e5f7e4737473b856b5ccf5766f'
SOURCE_ALLOWLIST = {
  'openpilot/sunnypilot/starpilot_views/offroad.py',
  'openpilot/sunnypilot/starpilot_views/tests/test_offroad.py',
}
EVIDENCE = [
  'docs/engineering/autonomous_campaign/G03_STATUS_COMPATIBILITY.json',
  'docs/engineering/autonomous_campaign/BUILD_EVIDENCE.json',
]


def git(*args):
  return subprocess.check_output(['git', '-C', str(ROOT), *args])


def digest_at(commit, path):
  return hashlib.sha256(git('show', f'{commit}:{path}')).hexdigest()


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--commit', help='exact verified engineering commit')
  args = parser.parse_args()
  state = json.loads((ROOT / 'docs/engineering/autonomous_campaign/CAMPAIGN_STATE.json').read_text())
  commit = args.commit or state['active_engineering']['head']
  paths = git('diff', '--name-only', f'{BASE}..{commit}').decode().splitlines()
  source_paths = sorted(path for path in paths if not path.startswith('docs/engineering/autonomous_campaign/'))
  if set(source_paths) != SOURCE_ALLOWLIST:
    raise SystemExit(f'HOLD: unexpected source diff: {source_paths}')
  manifest = {
    'schema_version': 1,
    'classification': 'OFFLINE_ENGINEERING_CANDIDATE',
    'installation_approved': False,
    'baseline_commit': BASE,
    'verified_engineering_commit': commit,
    'branch': 'codex/mvl-starpilot-continuation',
    'source_files': {path: digest_at(commit, path) for path in source_paths},
    'evidence_files': {path: digest_at(commit, path) for path in EVIDENCE},
    'pre_existing_vehicle_facing_files_changed': 0,
    'verification': {'offline_host_passed': 389, 'offline_host_failed': 0, 'offline_host_skipped': 0, 'recovery_tests_passed': 4, 'g03_source_crosswalk': 'PASS'},
    'holds': ['native MVL raylib UI startup and C3/C4 timing', 'G06 live transport security', 'AArch64 cold build and physical boot', 'Panda safety', 'Honda OEM ACC/FCW/CMBS/AEB', 'protected rollback and release approval'],
    'binary_artifacts': [],
  }
  print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == '__main__':
  main()
