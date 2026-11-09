#!/usr/bin/env python3
"""Fail-closed classification of an authenticated, passive comma 4 transcript.

This inventories evidence; it cannot authorize device compilation or install.
No device connection, imports from the installed source, or pickle reads occur.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

EXPECTED_SNAPSHOT_SHA256 = '21f732825d9d61580e44e7c33e67cd9f8f4904884e84e96f284641529f13740d'
FROZEN_SOURCE = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
_SHA = re.compile(r'[0-9a-f]{40}\Z')


def _single(raw: str, key: str) -> str | None:
    values = re.findall(rf'(?m)^{re.escape(key)}=([^\r\n]*)\r?$', raw)
    return values[0].strip() if len(values) == 1 else None


def evaluate(raw: str) -> dict:
    """Classify each prerequisite without interpreting absence as a safe value."""
    gates: dict[str, dict[str, str]] = {}

    def gate(name: str, status: str, reason: str) -> None:
        gates[name] = {'status': status, 'reason': reason}

    arch = _single(raw, 'ARCH')
    agnos = _single(raw, 'AGNOS_VERSION')
    gate('agnos_and_arch', 'PASS' if (arch, agnos) == ('aarch64', '19.9') else 'FAIL',
         'snapshot reports AGNOS 19.9 and aarch64' if (arch, agnos) == ('aarch64', '19.9') else 'exact AGNOS 19.9/aarch64 pair absent')
    installed = _single(raw, 'ACTIVE_COMMIT')
    gate('active_source_identity', 'PASS' if installed == FROZEN_SOURCE else 'FAIL' if installed and _SHA.fullmatch(installed) else 'UNKNOWN',
         'installed source matches frozen G10' if installed == FROZEN_SOURCE else 'installed source differs or is not authenticated as frozen G10')
    gate('staged_source_identity', 'UNKNOWN', 'no isolated staged checkout hash in passive transcript')
    gate('gpu_device_node', 'PASS' if re.search(r'(?m)^crw[^\r\n]*/dev/kgsl-3d0\r?$', raw) else 'UNKNOWN',
         'KGSL character node observed' if '/dev/kgsl-3d0' in raw else 'KGSL character node not observed')
    gate('gpu_chip_driver_abi', 'UNKNOWN', 'node presence does not identify GPU chip, driver, firmware or tinygrad ABI')
    offroad, onroad, ignition = (_single(raw, key) for key in ('OFFROAD_FLAG', 'ONROAD_FLAG', 'IGNITION_FLAG'))
    # A malformed concatenated value such as 1IGNITION_FLAG=UNKNOWN is never 1.
    flag_note = ('flags disagree or are incomplete' if (offroad, onroad, ignition) != ('1', '0', '0')
                 else 'flags are a point-in-time observation')
    gate('independent_live_parked', 'UNKNOWN', flag_note + '; independent live parked monitor absent')
    online = re.findall(r'(?m)^/sys/class/power_supply/(?:usb|dc|pc_port)/online=([^\r\n]*)\r?$', raw)
    gate('external_sustained_power', 'FAIL' if online and all(value == '0' for value in online) else 'UNKNOWN',
         'all observed external supply paths offline' if online and all(value == '0' for value in online) else 'sustained external power unproven')
    df = re.search(r'(?m)^/dev/\S+\s+\d+\s+\d+\s+(\d+)\s+\d+%\s+/data\r?$', raw)
    free_bytes = int(df.group(1)) if df else None
    gate('data_free_8gib_reserve', 'PASS' if free_bytes is not None and free_bytes >= 8 * 1024**3 else 'FAIL' if free_bytes is not None else 'UNKNOWN',
         'snapshot free bytes cover static 8 GiB reserve' if free_bytes is not None and free_bytes >= 8 * 1024**3 else 'snapshot free bytes below reserve or missing')
    gate('hard_quota_and_scratch_peak', 'UNKNOWN', 'no enforced isolated hard quota or measured scratch peak including model cache')
    mem = re.search(r'(?m)^MemAvailable:\s+(\d+) kB\r?$', raw)
    mem_kb = int(mem.group(1)) if mem else None
    gate('memory_headroom_and_peak', 'UNKNOWN', 'single MemAvailable observation; compiler CPU/GPU peak RSS and abort ceiling unmeasured')
    gate('thermal_and_gpu_error_monitor', 'UNKNOWN', 'untyped point temperatures; no continuous CPU/GPU thermal or GPU error monitor')
    gate('abort_and_rollback', 'UNKNOWN', 'isolated cleanup, abort and verified rollback not demonstrated')
    gate('non_driving_constraints', 'UNKNOWN', 'physical parked state and exclusion of driving not independently confirmed')
    return {
        'schema_version': 1,
        'decision': 'DEVICE_COMPILE_BLOCKED_UNVERIFIED_PARKED_OR_POWER_OR_RESOURCE',
        'network_readiness': 'DEVICE_CONNECTED_READONLY',
        'owner_state': 'B3_RESUMED_OWNER',
        'b3_outputs': 'B3_0_OF_6_AUTHENTIC',
        'device_compile_allowed': False,
        'device_write_performed': False,
        'install_allowed': False,
        'observations': {'data_free_bytes': free_bytes, 'mem_available_kb': mem_kb, 'external_supply_online_values': online},
        'gates': gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--expected-sha256', default=EXPECTED_SNAPSHOT_SHA256)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{64}', args.expected_sha256):
        parser.error('invalid expected hash')
    if not args.snapshot.is_file() or args.snapshot.is_symlink() or args.snapshot.stat().st_size > 1024 * 1024:
        parser.error('snapshot must be a bounded regular file')
    raw = args.snapshot.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.expected_sha256:
        parser.error('passive snapshot hash mismatch')
    report = evaluate(raw.decode('utf-8-sig'))
    report['evidence_sha256'] = args.expected_sha256
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
