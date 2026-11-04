#!/usr/bin/env python3
"""Validate a passive report's narrow classification; this does not qualify a release."""
import argparse
import json
from pathlib import Path
from .collect_health import STATES


def validate(data: dict) -> list[str]:
  if not isinstance(data, dict):
    return ['report must be an object']
  errors = []
  if data.get('profile') != 'COMMA4_NON_ACTUATING_MVL' or data.get('classification') != 'SUPPLEMENTAL_PASSIVE_DIAGNOSTIC':
    errors.append('invalid profile or classification')
  for section in ('parked_check', 'device', 'panda', 'car', 'processes', 'oem_collision_mitigation'):
    if not isinstance(data.get(section), dict) or data[section].get('status') not in STATES:
      errors.append('invalid '+section+' status')
  car = data.get('car') if isinstance(data.get('car'), dict) else {}
  mitigation = data.get('oem_collision_mitigation') if isinstance(data.get('oem_collision_mitigation'), dict) else {}
  if car.get('stock_acc_qualification') != 'NOT_TESTED':
    errors.append('stock ACC must remain NOT_TESTED')
  if mitigation.get('status') != 'NOT_TESTED':
    errors.append('OEM mitigation must remain NOT_TESTED')
  if data.get('release_gate') != 'NOT_APPLICABLE_TO_COMMA4_PROFILE':
    errors.append('passive report cannot become release gate')
  return errors


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument('report', type=Path)
  args = parser.parse_args()
  errors = validate(json.loads(args.report.read_text()))
  print('PASSIVE_REPORT_VALID' if not errors else 'INVALID: ' + ', '.join(errors))
  return 0 if not errors else 1


if __name__ == '__main__':
  raise SystemExit(main())
