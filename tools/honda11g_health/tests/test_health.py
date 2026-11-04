import json
from tools.honda11g_health.collect_health import make_report, render_markdown, items, number
from tools.honda11g_health.validate_report import validate


def test_observation_is_bounded_and_private_fields_are_never_serialized():
  messages = {
    'deviceState': {'started': False, 'freeSpacePercent': 65.0, 'cpuUsagePercent': [12, 25], 'cpuTempC': [52.1], 'vin': '1HGPRIVATEVIN1234'},
    'selfdriveState': {'enabled': False, 'active': False},
    'carState': {'vEgo': 0.0, 'cruiseState': {'enabled': False}, 'routeName': 'private-route'},
    'carParams': {'carFingerprint': 'HONDA_ACCORD_11G', 'carVin': '1HGPRIVATEVIN1234'},
    'pandaStates': [{'pandaType': 'chestnut', 'safetyModel': 'hondaBosch', 'safetyParam': 1, 'controlsAllowed': False,
                     'canState0': {'canfdEnabled': True, 'totalRxCnt': 10, 'totalRxLostCnt': 0, 'receiveErrorCnt': 0, 'busOffCnt': 0}}],
  }
  report = make_report(messages, agnos='19.8.1', source_sha='a'*40)
  encoded = json.dumps(report)
  assert '1HGPRIVATEVIN1234' not in encoded and 'private-route' not in encoded
  assert report['panda']['can_receive_buses'][0]['rx_count'] == 10
  assert report['car']['stock_acc_qualification'] == 'NOT_TESTED'
  assert report['oem_collision_mitigation']['status'] == 'NOT_TESTED'
  assert not validate(report)
  assert 'Supplemental diagnostic only' in render_markdown(report)


def test_motion_stops_and_missing_data_is_unavailable():
  report = make_report({'carState': {'vEgo': 4.0}, 'selfdriveState': {'active': True}})
  assert report['parked_check']['status'] == 'WARNING'
  assert report['device']['status'] == 'UNAVAILABLE'
  assert report['panda']['status'] == 'UNAVAILABLE'
  assert not validate(report)


def test_validator_refuses_false_safety_pass():
  report = make_report({})
  report['oem_collision_mitigation']['status'] = 'PASS_OBSERVED'
  report['car']['stock_acc_qualification'] = 'PASS_OBSERVED'
  assert len(validate(report)) == 2


def test_capnp_style_iterables_are_bounded():
  class Sequence:
    def __iter__(self):
      yield {'pandaType': 'chestnut'}
      raise AssertionError('read beyond bound')
  assert len(items(Sequence(), 1)) == 1
  report = make_report({'pandaStates': Sequence(), 'deviceState': {'cpuTempC': iter([52.0, 53.0])}})
  assert report['panda']['type'] == 'chestnut'
  assert report['device']['cpu_temp_c'] == [52.0, 53.0]


def test_malformed_input_fails_closed():
  assert number(10**1000) is None
  assert validate({'car': 'bad', 'oem_collision_mitigation': 'bad'})
