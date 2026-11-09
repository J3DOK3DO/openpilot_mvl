#!/usr/bin/env python3
"""Read-only B3 evidence admission. Never compiles, unpickles, or contacts a device."""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import json
from pathlib import Path

if __package__:
    from tools.release import mvl_model_artifacts as model
    from tools.release import qcom_b3_prepare as prep
else:
    import mvl_model_artifacts as model
    import qcom_b3_prepare as prep

WAIVER = 'OWNER_WAIVED_B2_OUTSTANDING_REQUIREMENTS_FOR_PLANNING_ONLY'
REQUIRED_EVIDENCE = ('provider_attestation_sha256', 'compiler_log_sha256',
                     'hard_quota_evidence_sha256', 'parked_monitor_evidence_sha256',
                     'gpu_thermal_evidence_sha256', 'memory_abort_evidence_sha256',
                     'quality_review_evidence_sha256')
PLAN_PATH = (Path(__file__).resolve().parents[2] / 'docs/engineering/autonomous_campaign'
             / 'B3C_SIX_TARGET_VERIFIED_PLAN_20261107.json')
PLAN_SHA256 = '6a493a0d9418f62310ee9a0f33d8e50ade4d5dc768cd54ec9c20ad45eaf3cd6e'
UNVERIFIED = 'UNVERIFIED_NATIVE_COMPILER_EXECUTION'
UNAUTHENTICATED = 'NATIVE_OUTPUT_PROVENANCE_NOT_AUTHENTICATED'


def trusted_plan() -> dict:
    """Load the frozen plan only after authenticating its exact checked-in bytes."""
    raw = model.regular(PLAN_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise ValueError('trusted B3C plan hash mismatch')
    return json.loads(raw, object_pairs_hook=model.no_duplicate_keys)


def audit(plan: dict, records: list[dict], artifacts: Path | None = None) -> dict:
    issues = []
    if json.dumps(plan, sort_keys=True) != json.dumps(trusted_plan(), sort_keys=True):
        issues.append('frozen native execution plan mismatch')
    if not isinstance(records, list) or any(not isinstance(x, dict) for x in records):
        raise ValueError('records must be an array of objects')
    if len(records) > 6:
        issues.append('too many capture records')
    names = [r.get('artifact') for r in records]
    if any(not isinstance(name, str) for name in names) or len(names) != len(set(name for name in names if isinstance(name, str))) or any(name not in model.ARTIFACTS for name in names):
        issues.append('duplicate or unknown artifact record')
    if records and not any(not isinstance(name, str) for name in names):
        issues += prep.validate_capture_records(records)
        if artifacts is None:
            issues.append('artifact directory required for byte verification')
        else:
            issues += prep.verify_artifact_set(artifacts, records)
        for record in records:
            for field in REQUIRED_EVIDENCE:
                value = record.get(field)
                if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                    issues.append(f"{record.get('artifact')}: missing {field}")
            if record.get('quality_result') != 'PASS_INDEPENDENT_REVIEW':
                issues.append(f"{record.get('artifact')}: quality review missing")
    static_issues = list(issues)
    count = len(records) if len(records) == 6 and not static_issues else 0
    if records:
        # Neither byte inspection nor self-reported receipts authenticate execution.
        issues.extend((UNVERIFIED, UNAUTHENTICATED))
    decision = UNVERIFIED if records else 'PREPARED_NO_QCOM_DEVICE'
    return {'schema_version': 1, 'decision': decision, 'b2_waiver': WAIVER,
            'b2_safety_status': 'NOT_SAFETY_ACCEPTED_NOT_PASSED',
            'static_candidates': count, 'b3_static_candidate_count': count,
            'receipt_authentication_status': 'SELF_REPORTED_NOT_AUTHENTICATED',
            'receipt_field_authentication': {
                field: 'SELF_REPORTED_NOT_AUTHENTICATED'
                for field in (*REQUIRED_EVIDENCE, 'quality_result')},
            'b3_verified_artifact_count': 0,
            'b3_required_artifact_count': 6, 'b3_completed_6_of_6': False,
            'issues': sorted(set(issues)), 'device_write_performed': False,
            'g10_promotion': False}


def load_json(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 1024 * 1024:
            raise ValueError('nonregular or oversized evidence JSON')
        data = stream.read(1024 * 1024 + 1)
        after = os.fstat(stream.fileno())
        if len(data) > 1024 * 1024 or (before.st_dev, before.st_ino,
                before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                after.st_ctime_ns):
            raise ValueError('oversized or changed evidence JSON')
    return json.loads(data, object_pairs_hook=model.no_duplicate_keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--records', type=Path)
    parser.add_argument('--artifacts', type=Path)
    args = parser.parse_args()
    # Reject nonregular/device paths without opening them, then guard against
    # a path-swap race using O_NOFOLLOW and descriptor-level fstat.
    try:
        model.regular(args.plan)
    except (OSError, ValueError):
        parser.error('B3C plan must be a regular non-symlink file')
    # Read once from a no-follow regular-file descriptor, capped at 1 MiB + 1.
    # Hash and parse exactly those same bytes to avoid a check/use race.
    try:
        fd = os.open(args.plan, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    except OSError:
        parser.error('cannot open B3C plan as a regular no-follow file')
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            parser.error('B3C plan must be a regular file')
        plan_bytes = stream.read(1024 * 1024 + 1)
    if len(plan_bytes) > 1024 * 1024:
        parser.error('supplied B3C plan exceeds 1 MiB limit')
    if hashlib.sha256(plan_bytes).hexdigest() != PLAN_SHA256:
        parser.error('supplied B3C plan hash mismatch')
    report = audit(json.loads(plan_bytes, object_pairs_hook=model.no_duplicate_keys),
                   load_json(args.records) if args.records else [], args.artifacts)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report['issues'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
