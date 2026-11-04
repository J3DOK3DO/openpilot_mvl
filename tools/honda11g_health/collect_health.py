#!/usr/bin/env python3
"""Bounded, passive, manual Honda 11G observation. No publishers or CAN/UDS commands."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from itertools import islice
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import time
from typing import Any

TOPICS = ('deviceState', 'selfdriveState', 'carState', 'pandaStates', 'carParams', 'managerState')
STATES = frozenset(('PASS_OBSERVED', 'WARNING', 'UNAVAILABLE', 'NOT_TESTED'))
_IDENTIFIER = re.compile(r'[A-Za-z0-9_.-]{1,64}\Z')


def field(value: Any, name: str) -> Any:
  if isinstance(value, dict):
    return value.get(name)
  try:
    return getattr(value, name, None)
  except Exception:
    return None


def items(value: Any, limit: int) -> list[Any]:
  if value is None or isinstance(value, (str, bytes, dict)):
    return []
  try:
    return list(islice(iter(value), limit))
  except (TypeError, ValueError):
    return []


def identity(value: Any) -> str | None:
  if value is None:
    return None
  text = str(value)
  return text if _IDENTIFIER.fullmatch(text) else None


def number(value: Any, low: float = 0, high: float = 1e12) -> int | float | None:
  if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
    return None
  try:
    if not math.isfinite(value):
      return None
  except (OverflowError, ValueError):
    return None
  return value


def observed(value: Any, note: str = 'Observation only; no safety qualification') -> dict[str, Any]:
  return {'status': 'PASS_OBSERVED' if value is not None else 'UNAVAILABLE', 'value': value, 'note': note}


def make_report(messages: dict[str, Any], *, agnos: str | None = None, source_sha: str | None = None,
                stopped_for_motion: bool = False) -> dict[str, Any]:
  """Project an explicit field allowlist; never serialize raw messages, VIN or route data."""
  device = messages.get('deviceState')
  selfdrive = messages.get('selfdriveState')
  car = messages.get('carState')
  params = messages.get('carParams')
  pandas = items(messages.get('pandaStates'), 1)
  panda = pandas[0] if pandas else None
  manager = messages.get('managerState')
  cruise = field(car, 'cruiseState')
  cpu = field(device, 'cpuUsagePercent')
  temps = field(device, 'cpuTempC')
  cpu = [number(x, 0, 100) for x in items(cpu, 16)]
  temps = [number(x, -40, 150) for x in items(temps, 16)]
  processes = field(manager, 'processes')
  process_summary = []
  if processes is not None:
    for item in items(processes, 64):
      name = identity(field(item, 'name'))
      if name in ('modeld', 'camerad', 'controlsd', 'ui', 'pandad', 'loggerd'):
        process_summary.append({'name': name, 'running': field(item, 'running') is True})
  buses = []
  for index in range(3):
    state = field(panda, f'canState{index}')
    if state is not None:
      buses.append({'bus': index, 'canfd_enabled': field(state, 'canfdEnabled') is True,
                    'rx_count': number(field(state, 'totalRxCnt')),
                    'rx_lost_count': number(field(state, 'totalRxLostCnt')),
                    'rx_error_count': number(field(state, 'receiveErrorCnt'), 0, 255),
                    'bus_off_count': number(field(state, 'busOffCnt'))})
  speed = number(field(car, 'vEgo'), 0, 100)
  active = field(selfdrive, 'active') is True or field(selfdrive, 'enabled') is True
  moving = stopped_for_motion or (speed is not None and speed > 0.1) or active
  report = {
    'schema_version': 1,
    'profile': 'COMMA4_NON_ACTUATING_MVL',
    'classification': 'SUPPLEMENTAL_PASSIVE_DIAGNOSTIC',
    'captured_at_utc': datetime.now(timezone.utc).isoformat(),
    'platform': {'os': platform.system(), 'arch': platform.machine(), 'agnos': identity(agnos), 'source_sha': source_sha if source_sha and re.fullmatch(r'[0-9a-f]{40}', source_sha) else None},
    'parked_check': {'status': 'WARNING' if moving else ('PASS_OBSERVED' if speed is not None else 'UNAVAILABLE'), 'v_ego_mps': speed, 'selfdrive_active_or_enabled': active, 'note': 'Stop collection if moving or selfdrive enabled; this does not prove parked state.'},
    'device': {'status': 'PASS_OBSERVED' if device is not None else 'UNAVAILABLE', 'started': field(device, 'started') if type(field(device, 'started')) is bool else None, 'free_space_percent': number(field(device, 'freeSpacePercent'), 0, 100), 'cpu_usage_percent': cpu, 'cpu_temp_c': temps},
    'panda': {'status': 'PASS_OBSERVED' if panda is not None else 'UNAVAILABLE', 'type': identity(field(panda, 'pandaType')), 'safety_model_observed': identity(field(panda, 'safetyModel')), 'safety_param_observed': number(field(panda, 'safetyParam'), 0, 65535), 'controls_allowed_observed': field(panda, 'controlsAllowed') if type(field(panda, 'controlsAllowed')) is bool else None, 'heartbeat_lost': field(panda, 'heartbeatLost') if type(field(panda, 'heartbeatLost')) is bool else None, 'can_receive_buses': buses, 'firmware_hash': {'status': 'UNAVAILABLE', 'note': 'No active firmware query is performed.'}},
    'car': {'status': 'PASS_OBSERVED' if car is not None else 'UNAVAILABLE', 'fingerprint': identity(field(params, 'carFingerprint')), 'cruise_enabled_observed': field(cruise, 'enabled') if type(field(cruise, 'enabled')) is bool else None, 'stock_acc_qualification': 'NOT_TESTED'},
    'processes': {'status': 'PASS_OBSERVED' if process_summary else 'UNAVAILABLE', 'items': process_summary},
    'oem_collision_mitigation': {'status': 'NOT_TESTED', 'note': 'Read-only observations cannot qualify FCW, CMBS, AEB or braking.'},
    'release_gate': 'NOT_APPLICABLE_TO_COMMA4_PROFILE',
  }
  return report


def render_markdown(report: dict[str, Any]) -> str:
  rows = [('Parked observation', report['parked_check']['status']), ('Device', report['device']['status']),
          ('Panda observation', report['panda']['status']), ('Car observation', report['car']['status']),
          ('Stock ACC qualification', report['car']['stock_acc_qualification']),
          ('OEM collision mitigation', report['oem_collision_mitigation']['status'])]
  return '# Passive Honda 11G health observation\n\nSupplemental diagnostic only. No OEM or vehicle-control safety qualification.\n\n| Area | Result |\n| --- | --- |\n' + ''.join(f'| {name} | {value} |\n' for name, value in rows)


def collect_device(seconds: int) -> tuple[dict[str, Any], bool]:
  from openpilot.cereal import messaging  # imported only after explicit --device --ack-parked
  sm = messaging.SubMaster(list(TOPICS), poll='deviceState')  # subscriber only
  deadline = time.monotonic() + seconds
  latest: dict[str, Any] = {}
  stopped = False
  for _ in range(min(seconds * 10, 150)):
    if time.monotonic() >= deadline: break
    sm.update(timeout=100)
    for topic in TOPICS:
      if sm.updated.get(topic) and sm.valid.get(topic):
        latest[topic] = sm[topic]
    car = latest.get('carState')
    selfdrive = latest.get('selfdriveState')
    speed = number(field(car, 'vEgo'), 0, 100)
    if (speed is not None and speed > 0.1) or field(selfdrive, 'active') is True or field(selfdrive, 'enabled') is True:
      stopped = True
      break
  return latest, stopped


def source_head() -> str | None:
  try:
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=2, check=True)
    sha = result.stdout.strip()
    return sha if re.fullmatch(r'[0-9a-f]{40}', sha) else None
  except (OSError, subprocess.SubprocessError):
    return None


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  mode = parser.add_mutually_exclusive_group(required=True)
  mode.add_argument('--device', action='store_true', help='manual local subscriber capture on a parked comma 4')
  mode.add_argument('--fixture', type=Path, help='offline fixture only; never opens messaging')
  parser.add_argument('--ack-parked', action='store_true')
  parser.add_argument('--seconds', type=int, default=5)
  parser.add_argument('--output-dir', type=Path, required=True)
  args = parser.parse_args()
  if args.seconds < 1 or args.seconds > 15: parser.error('--seconds must be 1..15')
  if args.device and not args.ack_parked: parser.error('--device requires --ack-parked')
  if args.fixture:
    raw = json.loads(args.fixture.read_text())
    if not isinstance(raw, dict): parser.error('fixture must be an object')
    messages, stopped = raw, False
  else:
    messages, stopped = collect_device(args.seconds)
  agnos_path = Path('/VERSION')
  agnos = agnos_path.read_text().strip() if agnos_path.is_file() else None
  report = make_report(messages, agnos=agnos, source_sha=source_head() if args.device else None, stopped_for_motion=stopped)
  args.output_dir.mkdir(parents=True, exist_ok=True)
  (args.output_dir / 'health.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
  (args.output_dir / 'health.md').write_text(render_markdown(report))
  print('PASSIVE_REPORT_WRITTEN')
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
