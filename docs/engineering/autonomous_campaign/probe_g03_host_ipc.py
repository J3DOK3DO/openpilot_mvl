import os
import time
from openpilot.cereal import messaging

checks = (
  ('deviceState', {'started': False, 'freeSpacePercent': 50.0, 'maxTempC': 42.0}),
  ('selfdriveState', {'enabled': True, 'active': False}),
  ('carState', {'vEgo': 13.5, 'cruiseState.enabled': True}),
)
for topic, expected in checks:
  endpoint = f'mvl_g03_offline_{os.getpid()}_{topic}'
  publisher = messaging.pub_sock(endpoint)
  subscriber = messaging.sub_sock(endpoint, timeout=100)
  message = messaging.new_message(topic, valid=True)
  payload = getattr(message, topic)
  for path, value in expected.items():
    target = payload
    segments = path.split('.')
    for segment in segments[:-1]:
      target = getattr(target, segment)
    setattr(target, segments[-1], value)
  encoded = message.to_bytes()
  for received in (messaging.log_from_bytes(encoded),):
    assert received.which() == topic
    for path, value in expected.items():
      actual = getattr(received, topic)
      for segment in path.split('.'):
        actual = getattr(actual, segment)
      assert actual == value, (topic, path, actual, value)
  received = None
  for _ in range(10):
    publisher.send(encoded)
    received = messaging.recv_one(subscriber)
    if received is not None:
      break
    time.sleep(0.05)
  assert received is not None and received.which() == topic, topic
  for path, value in expected.items():
    actual = getattr(received, topic)
    for segment in path.split('.'):
      actual = getattr(actual, segment)
    assert actual == value, (topic, path, actual, value)
  print(f'{topic}: PASS {len(expected)} primitive fields, capnp and local msgq IPC, {len(encoded)} bytes')
print('nested cruiseState access: PASS; 8 schema paths total')
