#!/usr/bin/env python3
"""Read-only B3 evidence admission. Never compiles, unpickles, or contacts a device."""
from __future__ import annotations

import argparse
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


def audit(plan: dict, records: list[dict], artifacts: Path | None = None) -> dict:
    issues = []
    if plan.get('source_commit') != prep.SOURCE or plan.get('tinygrad_commit') != prep.TINYGRAD or \
            plan.get('agnos', {}).get('image_sha256') != model.AGNOS199_IMAGE_SHA256 or \
            plan.get('agnos', {}).get('component_manifest_sha256') != model.AGNOS199_MANIFEST_SHA256 or \
            plan.get('handoff_manifest_sha256') != prep.HANDOFF_MANIFEST_SHA or \
            plan.get('handoff_tar_sha256') != prep.HANDOFF_TAR_SHA:
        issues.append('plan provenance mismatch')
    targets = plan.get('targets')
    if not isinstance(targets, list) or len(targets) != 6 or \
            [x.get('artifact') for x in targets if isinstance(x, dict)] != \
            [prep.FIRST] + [x for x in model.ARTIFACTS if x != prep.FIRST] or \
            any(x.get('stock_scons_target') != str(model.MODEL_DIR / x['artifact']) for x in targets if isinstance(x, dict)):
        issues.append('plan target sequence mismatch')
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
    count = len(records) if not issues else 0
    # Static bytes and self-reported hashes cannot authenticate a native provider.
    # An independent signed provider/reviewer workflow must issue completion.
    decision = 'B3_STATIC_6_OF_6_PENDING_AUTHENTICATION' if count == 6 else 'PREPARED_NO_QCOM_DEVICE'
    return {'schema_version': 1, 'decision': decision, 'b2_waiver': WAIVER,
            'b2_safety_status': 'NOT_SAFETY_ACCEPTED_NOT_PASSED',
            'b3_static_candidate_count': count, 'b3_verified_artifact_count': 0,
            'b3_required_artifact_count': 6, 'b3_completed_6_of_6': False,
            'issues': sorted(set(issues)), 'device_write_performed': False,
            'g10_promotion': False}


def load_json(path: Path):
    model.regular(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('oversized evidence JSON')
    return json.loads(path.read_text(), object_pairs_hook=model.no_duplicate_keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--records', type=Path)
    parser.add_argument('--artifacts', type=Path)
    args = parser.parse_args()
    report = audit(load_json(args.plan), load_json(args.records) if args.records else [], args.artifacts)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report['issues'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
