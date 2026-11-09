#!/usr/bin/env python3
"""Create an offline, explicitly non-installable C9 engineering bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import tarfile

from tools.release import combined_b3g10_gate, combined_rc_readiness

SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
DENY_BLOB = '40869f7450189f80dd9478b1fec674a83c80a1e2'
FILES = (
    'tools/release/c9_b3_pilot.py',
    'tools/release/c9_b3_receipt.py',
    'tools/release/c9_b3_windows_pilot.ps1',
    'tools/release/mvl_model_artifacts.py',
    'tools/release/qcom_b3_prepare.py',
    'tools/release/qcom_b2final.py',
    'tools/release/preflight_readonly.py',
    'docs/engineering/autonomous_campaign/B3_SIX_TARGET_DRY_RUN_20261107.json',
    'docs/engineering/autonomous_campaign/C9_B3_DEVICE_PILOT_20261109.md',
    'docs/engineering/autonomous_campaign/C9_G10_BUILD_20261109.json',
    'docs/engineering/autonomous_campaign/C9_R0_RELEASE_20261109.json',
)


def stage(repo: Path, output: Path) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError('output already exists')
    artifact_root = Path('/mnt/commadrive/MVL_C9_B3_G10_R0_ARTIFACTS_20261109')
    if not output.is_absolute() or not output.resolve().is_relative_to(artifact_root):
        raise ValueError('output must be under C9 artifacts')
    if subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == SOURCE:
        raise ValueError('engineering checkout confused with frozen product')
    blob = subprocess.check_output(['git', '-C', str(repo), 'rev-parse',
                                    'HEAD:docs/engineering/campaign_20261103/g03/G03_254_PARAMETER_EVIDENCE.json'], text=True).strip()
    if blob != DENY_BLOB:
        raise ValueError('protected Params evidence blob differs')
    crosswalk = json.loads(subprocess.check_output(['git', '-C', str(repo), 'show', blob]))
    if (not isinstance(crosswalk, dict) or crosswalk.get('approved_count') != 0 or
            crosswalk.get('denied_count') != 254 or len(crosswalk.get('entries', [])) != 254 or
            any(row.get('decision') != 'DENY' or row.get('read_enabled') is not False or
                row.get('write_enabled') is not False for row in crosswalk['entries'])):
        raise ValueError('protected Params evidence malformed')
    gate = combined_rc_readiness.evaluate(combined_b3g10_gate.evaluate())
    if gate['decision'] != 'RC_NOT_INSTALLABLE' or gate['install_allowed'] is not False:
        raise ValueError('unexpectedly promoted release gate')
    rows = []
    for rel in FILES:
        path = repo/rel
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or path.is_symlink():
            raise ValueError('nonregular package input: ' + rel)
        data = path.read_bytes()
        committed = subprocess.run(['git', '-C', str(repo), 'show', 'HEAD:'+rel],
                                   capture_output=True, check=True).stdout
        if data != committed:
            raise ValueError('package input differs from committed HEAD: ' + rel)
        rows.append({'path': rel, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    output.mkdir(mode=0o700)
    tar_path = output/'c9_engineering_hold.tar'
    with tarfile.open(tar_path, 'w') as tar:
        for row in rows:
            info = tarfile.TarInfo(row['path'])
            info.size = row['bytes']
            info.mode = 0o644
            info.mtime = 0
            with (repo/row['path']).open('rb') as stream:
                tar.addfile(info, stream)
    manifest = {'schema_version': 1, 'classification': 'NOT_INSTALLABLE_ENGINEERING_HOLD',
                'install_allowed': False, 'source_commit': SOURCE,
                'engineering_commit': subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], text=True).strip(),
                'protected_params_deny_blob': DENY_BLOB, 'protected_params_target_runtime': 'NOT_VERIFIED',
                'galaxy': 'OFF_UNREGISTERED_HISTORICAL_NOT_REVERIFIED',
                'starport': 'EXCLUDED', 'b3_verified_outputs': 0, 'g10_product': 'NOT_BUILT',
                'physical_checks_passed': 0, 'panda_firmware_version': 'NOT_CAPTURED',
                'backup_rollback': 'NOT_QUALIFIED', 'files': rows,
                'tar_sha256': hashlib.sha256(tar_path.read_bytes()).hexdigest(),
                'device_write_performed': False}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    try:
        report = stage(args.repo.resolve(), args.output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report = {'classification': 'NOT_INSTALLABLE_ENGINEERING_HOLD',
                  'install_allowed': False, 'error': str(exc)}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
