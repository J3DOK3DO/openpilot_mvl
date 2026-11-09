#!/usr/bin/env python3
"""Fail-closed, non-actuating QCOM artifact reuse qualification (never unpickles)."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from tools.release import mvl_model_artifacts as model

POLICY_REL = 'docs/engineering/autonomous_campaign/B3_SIGNED_REUSE_POLICY_20261109.json'
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_KINDS = ('compiler_log', 'monitor_log', 'abort_recovery_log', 'native_inference_log')
HEX = re.compile(r'^[0-9a-f]{64}$')
GIT_SHA = re.compile(r'^[0-9a-f]{40}$')


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def sha_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def read_regular(path: Path, maximum: int = 16 * 1024 * 1024) -> bytes:
    """Inspect and read one stable regular descriptor; prohibit symlink traversal."""
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
            raise ValueError('missing, empty, nonregular or oversized evidence: ' + str(path))
        data = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        if len(data) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
               before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                                       after.st_ctime_ns):
            raise ValueError('evidence changed during inspection: ' + str(path))
        return data


def json_file(path: Path) -> dict:
    item = json.loads(read_regular(path), object_pairs_hook=model.no_duplicate_keys)
    if type(item) is not dict:
        raise ValueError('evidence JSON must be an object')
    return item


def verified_git_policy(root: Path = ROOT) -> dict:
    """Policy is only accepted from its exact committed Git bytes, not a caller-supplied file."""
    repo = root.resolve()
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if not GIT_SHA.fullmatch(head):
        raise ValueError('invalid source commit')
    status = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain',
                                      '--untracked-files=all'], text=True)
    if status.strip():
        raise ValueError('engineering checkout must be clean')
    policy = read_regular(repo / POLICY_REL)
    committed = subprocess.check_output(['git', '-C', str(repo), 'show', 'HEAD:' + POLICY_REL])
    if committed != policy:
        raise ValueError('policy differs from committed source')
    return json.loads(policy, object_pairs_hook=model.no_duplicate_keys)


def inventory(directory: Path, policy: dict) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('candidate directory missing or symlink')
    required = policy['required_artifacts']
    if sorted(required) != sorted(model.ARTIFACTS):
        raise ValueError('policy artifact set differs from frozen source')
    actual = set(os.listdir(directory))
    results = {}
    for name in required:
        p = directory / name
        if name not in actual:
            results[name] = {'status': 'MISSING'}
            continue
        try:
            identity = model.qcom_capture(p)
            results[name] = {'status': 'STATIC_QCOM_SHAPE_ONLY_UNAUTHENTICATED', **identity}
        except (OSError, ValueError) as exc:
            results[name] = {'status': 'REJECTED_STATIC', 'reason': str(exc)[:240]}
    return {'decision': 'HOLD_REUSE_NOT_ADMITTED',
            'required': len(required),
            'static_candidates': sum(r['status'].startswith('STATIC_QCOM') for r in results.values()),
            'b3_verified_artifact_count': 0,
            'missing': sorted(name for name, item in results.items() if item['status'] == 'MISSING'),
            'extraneous': sorted(actual - set(required)),
            'results': results, 'device_contact': False, 'install_allowed': False}


def verify_signature(document: dict, signature_path: Path, policy: dict, role: str) -> bytes:
    signer = document.get('signer_id')
    key_text = policy['trusted_signers'][role].get(signer)
    if not isinstance(key_text, str):
        raise ValueError('untrusted ' + role + ' signer')
    try:
        public_bytes = base64.b64decode(key_text, validate=True)
        signature = base64.b64decode(read_regular(signature_path, 1024), validate=True)
        if len(public_bytes) != 32 or len(signature) != 64:
            raise ValueError('invalid signer key or signature length')
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, canonical(document))
    except (ValueError, binascii.Error, InvalidSignature) as exc:
        raise ValueError('invalid ' + role + ' signature') from exc
    return public_bytes


def verify_log(evidence_dir: Path, record: dict) -> None:
    filename, expected = record['file'], record['sha256']
    if (type(filename) is not str or not re.fullmatch('[A-Za-z0-9_.-]{1,100}', filename)
            or filename in ('.', '..') or not isinstance(expected, str) or not HEX.fullmatch(expected)):
        raise ValueError('unsafe evidence name or hash')
    actual = sha_bytes(read_regular(evidence_dir / filename))
    if actual != expected:
        raise ValueError('evidence file digest mismatch: ' + filename)


def assess_signed_reuse(directory: Path, evidence_dir: Path, capture_path: Path,
                        capture_signature: Path, review_path: Path, review_signature: Path,
                        graph_path: Path, policy: dict) -> dict:
    """Offline eligibility only: cannot independently attest physical truth or release."""
    stock = inventory(directory, policy)
    if stock['static_candidates'] != 6 or stock['missing'] or stock['extraneous']:
        raise ValueError('six exact structurally plausible captures required')
    if any(policy['trusted_signers'][role] == {} for role in ('producer', 'reviewer')):
        raise ValueError('no authorized producer/reviewer trust anchors enrolled')
    if evidence_dir.is_symlink() or not evidence_dir.is_dir():
        raise ValueError('evidence directory missing or symlink')
    capture, review, graph = json_file(capture_path), json_file(review_path), json_file(graph_path)
    if type(graph.get('files')) is not dict or len(graph['files']) != policy['source_graph_file_count']:
        raise ValueError('incomplete source dependency graph')
    if any(not isinstance(k, str) or not isinstance(v, str) or not HEX.fullmatch(v)
           for k, v in graph['files'].items()):
        raise ValueError('bad dependency graph entries')
    if sha_bytes(canonical(graph['files'])) != policy['source_graph_sha256']:
        raise ValueError('compiled source dependency graph differs from frozen source')
    for field in ('tinygrad_commit', 'agnos_image_sha256', 'onnx_sha256', 'recipe_sha256', 'flags'):
        if capture.get(field) != policy[field]:
            raise ValueError('pinned compile input mismatch: ' + field)
    if (capture.get('frozen_source_commit') != policy['source_commit']
            or not isinstance(capture.get('producer_source_commit'), str)
            or not GIT_SHA.fullmatch(capture['producer_source_commit'])
            or capture.get('source_graph_sha256') != policy['source_graph_sha256']
            or capture.get('gpu_backend') != 'QCOM'
            or capture.get('target_hardware') != 'COMMA4'
            or capture.get('agnos_version') != '19.9'):
        raise ValueError('runtime/source identity mismatch')
    records = capture.get('artifacts')
    if type(records) is not dict or set(records) != set(policy['required_artifacts']):
        raise ValueError('six exact capture record names required')
    for name, record in records.items():
        if type(record) is not dict or record.get('sha256') != stock['results'][name]['sha256'] or (
            type(record.get('bytes')) is not int or record['bytes'] != stock['results'][name]['size']):
            raise ValueError('captured artifact bytes do not match signed record: ' + name)
        evidence = record.get('evidence')
        if type(evidence) is not dict or set(evidence) != set(EVIDENCE_KINDS):
            raise ValueError('missing independent evidence files: ' + name)
        for value in evidence.values():
            if type(value) is not dict: raise ValueError('bad evidence file record')
            verify_log(evidence_dir, value)
    producer_pub = verify_signature(capture, capture_signature, policy, 'producer')
    if (review.get('capture_sha256') != sha_bytes(canonical(capture))
            or review.get('source_graph_sha256') != policy['source_graph_sha256']
            or review.get('conclusion') != 'PASS_INDEPENDENT_COMPATIBILITY_AND_NATIVE_EVIDENCE'
            or any(review.get(k) is not True for k in (
                'source_equivalence_verified', 'native_qcom_compilation_verified',
                'target_runtime_abi_verified', 'six_model_inference_verified',
                'abort_power_thermal_evidence_verified'))):
        raise ValueError('independent review evidence incomplete')
    reviewer_pub = verify_signature(review, review_signature, policy, 'reviewer')
    if producer_pub == reviewer_pub:
        raise ValueError('producer and reviewer must be distinct trust keys')
    return {'decision': 'ELIGIBLE_FOR_SEPARATE_B3_REUSE_ACCEPTANCE',
            'static_candidates': 6, 'signed_candidate_count': 6,
            'b3_verified_artifact_count': 0, 'install_allowed': False,
            'external_physical_truth_not_proven_by_signatures': True,
            'device_contact': False}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidates', type=Path, required=True)
    ap.add_argument('--evidence-dir', type=Path)
    ap.add_argument('--capture', type=Path)
    ap.add_argument('--capture-signature', type=Path)
    ap.add_argument('--review', type=Path)
    ap.add_argument('--review-signature', type=Path)
    ap.add_argument('--source-graph', type=Path)
    args = ap.parse_args()
    try:
        policy = verified_git_policy()
        full = [args.evidence_dir, args.capture, args.capture_signature,
                args.review, args.review_signature, args.source_graph]
        if any(v is not None for v in full):
            if not all(full): raise ValueError('all signed provenance inputs are mandatory together')
            result = assess_signed_reuse(args.candidates, args.evidence_dir, args.capture,
                args.capture_signature, args.review, args.review_signature, args.source_graph, policy)
        else:
            result = inventory(args.candidates, policy)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        result = {'decision': 'HOLD_REUSE_NOT_ADMITTED', 'reason': str(exc),
                  'b3_verified_artifact_count': 0, 'install_allowed': False, 'device_contact': False}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2  # Qualification by itself never promotes a device release or B3 acceptance.


if __name__ == '__main__':
    raise SystemExit(main())
