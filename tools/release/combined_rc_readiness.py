#!/usr/bin/env python3
"""Offline RC admission and installation rehearsal. Never contacts a device."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from tools.release import combined_b3g10_gate as gate

SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
KNOWN_GOOD = 'a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1'
PROFILE = 'COMMA4_NON_ACTUATING_MVL'
DECISION = 'RC_NOT_INSTALLABLE'


def _row(name: str, status: str, evidence: str, needed: str) -> dict[str, str]:
    return {'requirement': name, 'status': status, 'evidence': evidence,
            'next_proof': needed}


def evaluate(base: Mapping[str, object]) -> dict[str, object]:
    """Derive a conservative matrix only from the pinned offline gate.

    A caller cannot supply positive hardware/build claims to this evaluator.
    The upstream gate authenticates its historical inputs, but its local
    artifact inventory is metadata only. Any unexpected upstream state fails.
    """
    if (type(base) is not dict or base.get('source_commit') != SOURCE or
            base.get('decision') != gate.DECISION or
            base.get('plan_sha256') != gate.PLAN_SHA256 or
            base.get('recovery_sha256') != gate.RECOVERY_SHA256 or
            base.get('install_allowed') is not False or
            base.get('b3_verified_artifact_count') != 0 or
            base.get('g10_cold_build') != 'NOT_BUILT' or
            base.get('physical_checks_passed') != 0):
        raise ValueError('untrusted or unexpectedly promoted upstream evidence')
    inventory = base.get('artifact_inventory')
    if type(inventory) is not dict or set(inventory) != set(gate.NAMES):
        raise ValueError('six-target inventory is incomplete')
    if any(value not in ('ABSENT_IN_LOCAL_CHECKOUT', 'PRESENT_UNVERIFIED')
           for value in inventory.values()):
        raise ValueError('unexpected artifact inventory result')
    present = sum(value == 'PRESENT_UNVERIFIED' for value in inventory.values())
    if base.get('b3_local_present_count') != present:
        raise ValueError('artifact inventory count mismatch')
    checks = [
        _row('C1 non-actuating source integration', 'PASSED_HOST_SCOPE',
             'Pinned source is unchanged from frozen 4b product; historical host tests are separately recorded',
             'Native UI, IPC, startup, fault and Honda display checks on a qualified device'),
        _row('C2 six QCOM captures', 'BLOCKED', f'{present}/6 locally present; 0/6 authenticated',
             'Authenticated source-matched QCOM execution, six hashes and target quality review'),
        _row('C3 full AGNOS 19.9 product', 'BLOCKED', 'Complete cold build NOT_BUILT',
             'Six verified QCOM inputs, exact cold build, binary/ABI and package closure'),
        _row('C4 host release regression', 'PASSED_HISTORICAL_SCOPE',
             'Prior exact-commit host suites recorded; current campaign result is separate',
             'Rerun current changed-tool suite at exact committed HEAD'),
        _row('C4 254 restricted Params', 'REQUIRED_DENY',
             'Historical 254-key DENY crosswalk at frozen product source',
             'Keep all 254 denied; target runtime proof remains separate'),
        _row('C4 G06 transport', 'OFF_CONDITIONAL_NA',
             'Production registration remains OFF in the restricted release profile',
             'Separate target security qualification before any future registration'),
        _row('C4 physical C4-01–07 and C4-09–11', 'NOT_RUN',
             '0/10 applicable target checks accepted',
             'Complete product, separate authorization and actual bench evidence'),
        _row('C5 package and installation', 'BLOCKED',
             'No installable package, physical qualification or installation approval',
             'Package integrity, known-good backup, migration, health and owner approval'),
        _row('C4-08 optional G06 check', 'NOT_APPLICABLE',
             'Conditional only while G06 stays unregistered',
             'Reopen if production transport is registered'),
        _row('C4-12 restoration exercise', 'WAIVED_BY_OWNER_NOT_EXECUTED',
             'Owner waiver applies to this profile; no restoration test was run',
             'Owner-managed previous-version reinstall if a later approved installation fails'),
    ]
    return {
        'schema_version': 1, 'profile': PROFILE, 'source_commit': SOURCE,
        'known_good_commit_reference': KNOWN_GOOD,
        'known_good_currently_verified': False,
        'decision': DECISION, 'install_allowed': False,
        'device_write_performed': False, 'device_contact_performed': False,
        'b2_safety': 'NOT_PASSED_PLANNING_WAIVER_ONLY',
        'b3_verified_qcom_outputs': 0, 'b3_required_qcom_outputs': 6,
        'g10_product': 'NOT_BUILT', 'applicable_physical_checks_passed': 0,
        'applicable_physical_checks_required': 10,
        'formal_scoped_acceptance': {'accepted': 12, 'applicable': 25, 'percent': 48},
        'release_approval': 'HOLD',
        'checks': checks,
        'installation_sequence': [
            'Verify exact approved branch, product package, hashes and AGNOS identity',
            'Independently verify parked and disengaged target, known-good branch/SHA and backup',
            'Validate Params migration without changing protected 254-key DENY policy',
            'Obtain separate owner approval for installation',
            'Only then execute a separately reviewed device installation procedure',
            'Run C4 health, UI, IPC, warning and stock-behavior checks',
            'On failure stop activation and follow owner-managed known-good reinstall',
        ],
        'installation_sequence_status': 'PLAN_ONLY_NOT_EXECUTED',
    }


def rehearse(events: Sequence[str]) -> dict[str, object]:
    """Pure mock failure-response rehearsal; no filesystem or subprocess action."""
    allowed = {'preflight_ok', 'backup_ok', 'stage_ok', 'switch_ok', 'health_ok',
               'stage_failed', 'switch_failed', 'health_failed'}
    if type(events) not in (list, tuple) or not events or any(type(e) is not str or e not in allowed for e in events):
        raise ValueError('invalid rehearsal event')
    steps = []
    expected = ['preflight_ok', 'backup_ok', 'stage_ok', 'switch_ok', 'health_ok']
    for index, event in enumerate(events):
        if index >= len(expected):
            raise ValueError('rehearsal has extra events')
        if event == expected[index]:
            steps.append(event)
            continue
        if index < 2 or event != expected[index].replace('_ok', '_failed') or index != len(events) - 1:
            raise ValueError('invalid failure transition')
        return {'mode': 'MOCK_ONLY', 'result': 'STOP_OWNER_RECOVERY_REQUIRED',
                'last_event': event, 'known_good_reference': KNOWN_GOOD,
                'known_good_modified': False, 'device_write_performed': False}
    if len(steps) != len(expected):
        return {'mode': 'MOCK_ONLY', 'result': 'INCOMPLETE_NO_INSTALL',
                'known_good_modified': False, 'device_write_performed': False}
    return {'mode': 'MOCK_ONLY', 'result': 'SIMULATED_FLOW_ONLY_NO_INSTALL_AUTHORITY',
            'known_good_modified': False, 'device_write_performed': False}


def main() -> int:
    try:
        report = evaluate(gate.evaluate())
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({'decision': DECISION, 'install_allowed': False,
                          'input_error': str(error)}, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2  # A plan is never install authorization.


if __name__ == '__main__':
    raise SystemExit(main())
