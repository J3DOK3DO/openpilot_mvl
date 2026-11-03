#!/usr/bin/env python3
"""Verify the pinned source for the read-only G03 status field subset."""
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
NATIVE = Path('/mnt/commadrive/MVL_NATIVE_LATEST_20261103')
EXPECTED_NATIVE = '376c44b5731b2655e5c2f301b73c9729eb499e91'
EXPECTED_OPENDDBC = '3fec9a418a659de31d7b1f494193161697a35071'
SOURCES = {
  'log': (NATIVE / 'openpilot/cereal/log.capnp', 'be3b81471c18ad7ffbac3890042cd93823c69832fd88130ac9400bd02f8b049b'),
  'car': (NATIVE / 'opendbc_repo/opendbc/car/car.capnp', 'f39cc7be3216e3b692334b4c7dc7fc5f6509865e700b15e17acccc7b7cc644ab'),
}
FIELDS = [
  ('deviceState', 'started', 'Bool', 11, 'log', '  started @11 :Bool;'),
  ('deviceState', 'freeSpacePercent', 'Float32', 7, 'log', '  freeSpacePercent @7 :Float32;'),
  ('deviceState', 'maxTempC', 'Float32', 44, 'log', '  maxTempC @44 :Float32;'),
  ('selfdriveState', 'enabled', 'Bool', 1, 'log', '  enabled @1 :Bool;'),
  ('selfdriveState', 'active', 'Bool', 2, 'log', '  active @2 :Bool;'),
  ('carState', 'vEgo', 'Float32', 1, 'car', '  vEgo @1 :Float32;'),
  ('carState', 'cruiseState', 'CruiseState', 10, 'car', '  cruiseState @10 :CruiseState;'),
  ('carState', 'cruiseState.enabled', 'Bool', 0, 'car', '    enabled @0 :Bool;'),
]


def git_head(path):
  return subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()


def struct_body_lines(source_text: str, struct_name: str) -> list[str]:
  """Return only direct declarations inside the uniquely named struct."""
  pattern = rf'(?m)^\s*struct\s+{re.escape(struct_name)}(?:\s+@[^ {{]+)?\s*\{{'
  matches = list(re.finditer(pattern, source_text))
  assert len(matches) == 1, f'expected one {struct_name} struct'
  depth = 1
  direct = []
  for line in source_text[matches[0].end():].splitlines():
    code = line.split('#', 1)[0].strip()
    if depth == 1 and code:
      direct.append(code)
    depth += code.count('{') - code.count('}')
    if depth == 0:
      return direct
  raise AssertionError(f'unclosed {struct_name} struct')


def main():
  assert git_head(NATIVE) == EXPECTED_NATIVE, 'native source SHA changed'
  assert git_head(NATIVE / 'opendbc_repo') == EXPECTED_OPENDDBC, 'opendbc SHA changed'
  text = {}
  for key, (path, expected) in SOURCES.items():
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected, f'{key} source hash changed'
    text[key] = data.decode()
  assert (ROOT / 'openpilot/cereal/log.capnp').read_bytes() == SOURCES['log'][0].read_bytes(), 'checkout log schema differs'
  params = json.loads((ROOT / 'docs/engineering/campaign_20261103/g03/G03_254_PARAMETER_EVIDENCE.json').read_text())
  assert params['entry_count'] == params['denied_count'] == len(params['entries']) == 254 and params['approved_count'] == 0
  assert all(entry['decision'] == 'DENY' and entry['read_enabled'] is False and entry['write_enabled'] is False for entry in params['entries']), 'Params quarantine entry changed'
  result = []
  assert any(line.startswith('struct CruiseState {') for line in struct_body_lines(text['car'], 'CarState')), 'CruiseState is not nested in CarState'
  for topic, field, typ, ordinal, source, declaration in FIELDS:
    struct = {'deviceState': 'DeviceState', 'selfdriveState': 'SelfdriveState', 'carState': 'CarState'}[topic]
    if field == 'cruiseState.enabled':
      struct = 'CruiseState'
    assert any(line.startswith(declaration.strip()) for line in struct_body_lines(text[source], struct)), f'missing {topic}.{field}'
    result.append({'topic':topic,'field':field,'type':typ,'ordinal':ordinal,'source':source,'decision':'SCHEMA_SOURCE_PASS_RUNTIME_HOLD'})
  print(json.dumps({'schema_version':1,'native_source_sha':EXPECTED_NATIVE,'opendbc_sha':EXPECTED_OPENDDBC,'source_sha256':{k:v[1] for k,v in SOURCES.items()},'field_decisions':result,'params_decision':{'denied':254,'approved':0},'ipc_abi_decision':'HOLD','device_runtime_decision':'HOLD'},indent=2))


if __name__ == '__main__':
  try: main()
  except (AssertionError, OSError, subprocess.CalledProcessError) as exc:
    print(f'HOLD: {exc}',file=sys.stderr)
    sys.exit(2)
