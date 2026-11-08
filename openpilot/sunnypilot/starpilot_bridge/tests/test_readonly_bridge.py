from __future__ import annotations

import ast
import threading
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from openpilot.sunnypilot.starpilot_bridge import Feature, FeatureConfigurationError, FeatureRegistry, ReadOnlyStatusAdapter
from openpilot.sunnypilot.starpilot_bridge.factory import create_mvl_submaster


NOW = 10_000_000_000


class FakeSubMaster:
  def __init__(self, states=None, *, alive=None, valid=None, timestamps=None):
    self.states = states or {}
    self.alive = alive if alive is not None else {topic: True for topic in self.states}
    self.valid = valid if valid is not None else {topic: True for topic in self.states}
    self.logMonoTime = timestamps if timestamps is not None else {topic: NOW - 1 for topic in self.states}
    self.accesses = []

  def __getitem__(self, topic):
    self.accesses.append(topic)
    return self.states[topic]


class UntouchableSource:
  def __getattribute__(self, _name):
    raise AssertionError("default-off adapter touched its source")


def device(*, started=True, free=55.0, temp=42.0):
  return SimpleNamespace(started=started, freeSpacePercent=free, maxTempC=temp)


def selfdrive(*, enabled=True, active=True):
  return SimpleNamespace(enabled=enabled, active=active)


def car(*, speed=13.5, cruise=True, **identity):
  value = SimpleNamespace(vEgo=speed, cruiseState=SimpleNamespace(enabled=cruise))
  for key, item in identity.items():
    setattr(value, key, item)
  return value


def enabled(*features):
  return FeatureRegistry.from_overrides({feature.value: True for feature in features})


def adapter(source, registry, now=lambda: NOW, **kwargs):
  return ReadOnlyStatusAdapter(source, registry=registry, now_ns=now, **kwargs)


def reasons(snapshot):
  return [rejection.reason for rejection in snapshot.rejections]


def test_defaults_are_all_off_and_do_not_touch_source():
  registry = FeatureRegistry()
  assert registry.active_topics() == ()
  snapshot = adapter(UntouchableSource(), registry).read()
  assert snapshot.device is snapshot.selfdrive is snapshot.car is None
  assert snapshot.rejections == ()


@pytest.mark.parametrize("key", ["unknown", "DEVICE_STATUS", "", 4])
def test_unknown_feature_keys_fail(key):
  with pytest.raises(FeatureConfigurationError):
    FeatureRegistry.from_overrides({key: True})


@pytest.mark.parametrize("value", [1, 0, "true", None, 1.0])
def test_feature_values_must_be_exact_bools(value):
  with pytest.raises(FeatureConfigurationError):
    FeatureRegistry.from_overrides({"device_status": value})


def test_feature_registry_is_immutable():
  registry = FeatureRegistry()
  with pytest.raises(TypeError):
    registry.values[Feature.DEVICE_STATUS] = True


def test_explicit_factory_rejects_all_off_before_cereal_import():
  with pytest.raises(ValueError, match="disabled"):
    create_mvl_submaster(FeatureRegistry())


def test_valid_snapshots_are_typed_immutable_and_read_only():
  source = FakeSubMaster({"deviceState": device(), "selfdriveState": selfdrive(), "carState": car()})
  snapshot = adapter(source, enabled(Feature.DEVICE_STATUS, Feature.SELFDRIVE_STATUS, Feature.CAR_STATUS)).read()
  assert snapshot.device and snapshot.device.free_space_percent == 55.0
  assert snapshot.selfdrive and snapshot.selfdrive.active is True
  assert snapshot.car and snapshot.car.v_ego_mps == 13.5 and snapshot.car.cruise_enabled is True
  assert source.accesses == ["deviceState", "selfdriveState", "carState"]
  with pytest.raises(FrozenInstanceError):
    snapshot.car.v_ego_mps = 0.0


def test_enabled_topic_missing_from_source_is_rejected():
  snapshot = adapter(FakeSubMaster(), enabled(Feature.DEVICE_STATUS)).read()
  assert snapshot.device is None
  assert reasons(snapshot) == ["missing_topic"]


@pytest.mark.parametrize("attribute,value,reason", [("alive", False, "not_alive"), ("valid", False, "not_valid"), ("alive", 1, "not_alive"), ("valid", 1, "not_valid")])
def test_alive_and_valid_must_be_exact_true(attribute, value, reason):
  source = FakeSubMaster({"deviceState": device()})
  getattr(source, attribute)["deviceState"] = value
  snapshot = adapter(source, enabled(Feature.DEVICE_STATUS)).read()
  assert snapshot.device is None
  assert reasons(snapshot) == [reason]


@pytest.mark.parametrize("timestamp,reason", [(NOW - 2_000_000_001, "stale_timestamp"), (NOW + 1, "future_timestamp"), (0, "invalid_timestamp"), (-1, "invalid_timestamp"), (1.0, "invalid_timestamp")])
def test_bad_timestamps_fail_closed(timestamp, reason):
  source = FakeSubMaster({"deviceState": device()}, timestamps={"deviceState": timestamp})
  snapshot = adapter(source, enabled(Feature.DEVICE_STATUS)).read()
  assert snapshot.device is None
  assert reasons(snapshot) == [reason]


def test_out_of_order_timestamp_is_rejected_without_replacing_snapshot_state():
  source = FakeSubMaster({"deviceState": device()}, timestamps={"deviceState": NOW - 10})
  reader = adapter(source, enabled(Feature.DEVICE_STATUS))
  assert reader.read().device is not None
  source.logMonoTime["deviceState"] = NOW - 11
  assert reasons(reader.read()) == ["out_of_order_timestamp"]


def test_concurrent_read_fails_closed_without_rewinding_timestamp_state():
  entered = threading.Event()
  release = threading.Event()

  class PausedSource(FakeSubMaster):
    def __init__(self):
      super().__init__({"deviceState": device()})
      self.logMonoTime["deviceState"] = NOW - 100

    def __getitem__(self, topic):
      if threading.current_thread().name == "bridge-first-reader":
        entered.set()
        assert release.wait(2)
      return super().__getitem__(topic)

  source = PausedSource()
  reader = adapter(source, enabled(Feature.DEVICE_STATUS))
  first: list = []
  worker = threading.Thread(target=lambda: first.append(reader.read()), name="bridge-first-reader")
  worker.start()
  try:
    assert entered.wait(2)
    source.logMonoTime["deviceState"] = NOW - 99
    assert reasons(reader.read()) == ["concurrent_read"]
  finally:
    release.set()
    worker.join(2)
  assert not worker.is_alive()
  assert first[0].device is not None
  assert reader.read().device is not None
  assert reasons(reader.read()) == ["out_of_order_timestamp"]


def test_concurrent_producer_can_pair_old_metadata_with_new_state_without_snapshot_contract():
  timestamp_read = threading.Event()
  producer_done = threading.Event()
  source = FakeSubMaster({"deviceState": device(free=10.0)},
                         timestamps={"deviceState": NOW - 100})

  class PausingTimestamps(dict):
    def __getitem__(self, topic):
      old_timestamp = super().__getitem__(topic)
      timestamp_read.set()
      assert producer_done.wait(2)
      return old_timestamp

  source.logMonoTime = PausingTimestamps(source.logMonoTime)

  def produce():
    assert timestamp_read.wait(2)
    source.states["deviceState"] = device(free=90.0)
    source.logMonoTime["deviceState"] = NOW - 1
    producer_done.set()

  producer = threading.Thread(target=produce, name="synthetic-producer")
  producer.start()
  try:
    snapshot = adapter(source, enabled(Feature.DEVICE_STATUS)).read()
  finally:
    producer_done.set()
    producer.join(2)
  assert not producer.is_alive()
  # This is a documented source-contract limitation, not an acceptance gate:
  # the adapter cannot atomically sample a caller-owned producer's mappings.
  assert snapshot.device is not None
  assert snapshot.device.timestamp_ns == NOW - 100
  assert snapshot.device.free_space_percent == 90.0


def test_clock_rollback_returns_no_topics_and_recovers_on_fresh_time():
  source = FakeSubMaster({"deviceState": device()}, timestamps={"deviceState": NOW - 10})
  times = iter((NOW, NOW - 1, NOW + 1))
  reader = adapter(source, enabled(Feature.DEVICE_STATUS), now=lambda: next(times))
  first = reader.read()
  assert first.device is not None
  rollback = reader.read()
  assert rollback.device is None
  assert reasons(rollback) == ["clock_rollback"]
  source.logMonoTime["deviceState"] = NOW - 5
  recovered = reader.read()
  assert recovered.device is not None
  assert recovered.now_ns == NOW + 1


def test_clock_rollback_does_not_read_any_topic():
  source = FakeSubMaster({"deviceState": device()}, timestamps={"deviceState": NOW - 10})
  times = iter((NOW, NOW - 1))
  reader = adapter(source, enabled(Feature.DEVICE_STATUS), now=lambda: next(times))
  assert reader.read().device is not None
  source.accesses.clear()
  snapshot = reader.read()
  assert reasons(snapshot) == ["clock_rollback"]
  assert source.accesses == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), -0.01, 100.01, "55"])
def test_bad_device_storage_values_are_rejected(value):
  source = FakeSubMaster({"deviceState": device(free=value)})
  snapshot = adapter(source, enabled(Feature.DEVICE_STATUS)).read()
  assert snapshot.device is None
  assert reasons(snapshot) in (["out_of_range"], ["malformed_state"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, 150.01, "42"])
def test_bad_temperature_values_are_rejected(value):
  source = FakeSubMaster({"deviceState": device(temp=value)})
  snapshot = adapter(source, enabled(Feature.DEVICE_STATUS)).read()
  assert snapshot.device is None
  assert reasons(snapshot) in (["out_of_range"], ["malformed_state"])


@pytest.mark.parametrize("state", [device(started=1), selfdrive(enabled="yes"), car(speed=-0.1), car(speed=100.1), SimpleNamespace(vEgo=1.0, cruiseState=SimpleNamespace(enabled=1))])
def test_malformed_or_out_of_range_state_is_rejected(state):
  topic = "deviceState" if hasattr(state, "freeSpacePercent") else "selfdriveState" if hasattr(state, "active") else "carState"
  feature = {"deviceState": Feature.DEVICE_STATUS, "selfdriveState": Feature.SELFDRIVE_STATUS, "carState": Feature.CAR_STATUS}[topic]
  snapshot = adapter(FakeSubMaster({topic: state}), enabled(feature)).read()
  assert getattr(snapshot, {"deviceState": "device", "selfdriveState": "selfdrive", "carState": "car"}[topic]) is None
  assert reasons(snapshot)[0] in {"malformed_state", "out_of_range"}


def test_source_and_clock_exceptions_do_not_escape():
  class BrokenSource:
    @property
    def alive(self):
      raise RuntimeError("process failed")

  snapshot = adapter(BrokenSource(), enabled(Feature.DEVICE_STATUS)).read()
  assert reasons(snapshot) == ["missing_topic"]
  clock_snapshot = adapter(FakeSubMaster(), enabled(Feature.DEVICE_STATUS), now=lambda: (_ for _ in ()).throw(RuntimeError())).read()
  assert reasons(clock_snapshot) == ["clock_failure"]


def test_adapter_never_mutates_source_input_or_projects_identity():
  state = car(vin="not-projected", fingerprint="not-projected")
  source = FakeSubMaster({"carState": state})
  original_alive = dict(source.alive)
  original_valid = dict(source.valid)
  original_times = dict(source.logMonoTime)
  snapshot = adapter(source, enabled(Feature.CAR_STATUS)).read()
  assert snapshot.car is not None and not hasattr(snapshot.car, "vin") and not hasattr(snapshot.car, "fingerprint")
  assert source.alive == original_alive and source.valid == original_valid and source.logMonoTime == original_times
  assert state.vin == "not-projected" and state.fingerprint == "not-projected"


def test_package_sources_have_no_privileged_or_side_effect_imports_or_writes():
  package = Path(__file__).resolve().parents[1]
  forbidden_import_roots = {"os", "subprocess", "socket", "requests", "urllib", "pathlib", "multiprocessing"}
  forbidden_names = {"open", "exec", "eval", "system", "Popen", "run", "write_text", "write_bytes"}
  for path in package.glob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not imported & forbidden_import_roots, path
    assert not called & forbidden_names, path
    source = path.read_text(encoding="utf-8")
    assert "PubMaster" not in source
    assert "common.params" not in source and ".put(" not in source
