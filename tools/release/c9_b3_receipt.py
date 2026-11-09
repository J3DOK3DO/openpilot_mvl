#!/usr/bin/env python3
"""Static first-warp receipt audit. Never unpickles or authenticates execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.release import mvl_model_artifacts as model
from tools.release.c9_b3_pilot import FIRST, FIRST_TARGET, SOURCE, TINYGRAD, checked_plan


def verify(receipt: dict, artifact: Path, log: Path) -> dict:
    checked_plan()
    issues = []
    if (receipt.get('source_commit') != SOURCE or receipt.get('tinygrad_commit') != TINYGRAD or
            receipt.get('target') != FIRST_TARGET or receipt.get('artifact') != FIRST or
            receipt.get('compiler_exit_code') != 0 or receipt.get('gpu_backend') != 'QCOM'):
        issues.append('source, target or compiler identity mismatch')
    try:
        actual = model.qcom_capture(artifact)
        if artifact.name != FIRST or actual != {'sha256': receipt.get('sha256'), 'size': receipt.get('bytes')}:
            issues.append('captured bytes differ from receipt')
    except (OSError, ValueError) as exc:
        issues.append('invalid captured bytes: ' + str(exc))
    try:
        if model.sha256(model.regular(log)) != receipt.get('compiler_log_sha256'):
            issues.append('compiler log hash mismatch')
    except (OSError, ValueError) as exc:
        issues.append('missing compiler log: ' + str(exc))
    return {'decision': 'STATIC_CANDIDATE_UNAUTHENTICATED' if not issues else 'HOLD',
            'issues': issues, 'b3_verified_artifact_count': 0,
            'independently_authenticated': False, 'g10_promotion': False,
            'artifact': FIRST, 'device_write_performed': False}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--receipt', type=Path, required=True)
    ap.add_argument('--artifact', type=Path, required=True)
    ap.add_argument('--log', type=Path, required=True)
    args = ap.parse_args()
    try:
        receipt = json.loads(model.regular(args.receipt).read_bytes(), object_pairs_hook=model.no_duplicate_keys)
        result = verify(receipt, args.artifact, args.log)
    except (OSError, ValueError, KeyError) as exc:
        result = {'decision': 'HOLD', 'issues': [str(exc)], 'b3_verified_artifact_count': 0,
                  'g10_promotion': False, 'device_write_performed': False}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
