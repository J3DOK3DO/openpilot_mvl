"""Factory contract tests: no car, sockets, Params writes or CAN traffic."""

from __future__ import annotations

import builtins
import sys
from types import ModuleType

import pytest

from openpilot.sunnypilot.starpilot_bridge.factory import create_mvl_submaster
from openpilot.sunnypilot.starpilot_bridge.features import Feature, FeatureRegistry


def test_all_off_never_attempts_native_import(monkeypatch):
  original_import = builtins.__import__
  attempted = []

  def watched_import(name, *args, **kwargs):
    if name.startswith("openpilot.cereal") or name == "cereal":
      attempted.append(name)
      raise AssertionError("no native message import permitted when OFF")
    return original_import(name, *args, **kwargs)

  monkeypatch.setattr(builtins, "__import__", watched_import)
  with pytest.raises(ValueError, match="disabled"):
    create_mvl_submaster(FeatureRegistry())
  assert attempted == []


def test_wrong_registry_rejected_before_import():
  with pytest.raises(TypeError, match="FeatureRegistry"):
    create_mvl_submaster({"device_status": True})


def test_factory_constructs_exact_native_readonly_topics(monkeypatch):
  subscribers = []
  module = ModuleType("openpilot.cereal")

  class NativeMessaging:
    @staticmethod
    def SubMaster(topics):
      subscribers.append(tuple(topics))
      return object()

  module.messaging = NativeMessaging
  monkeypatch.setitem(sys.modules, "openpilot.cereal", module)

  registry = FeatureRegistry.from_overrides({
    Feature.DEVICE_STATUS: True,
    Feature.SELFDRIVE_STATUS: True,
    Feature.CAR_STATUS: False,
  })
  result = create_mvl_submaster(registry)
  assert result is not None
  assert subscribers == [("deviceState", "selfdriveState")]


def test_all_features_on_remain_subscriptions_only(monkeypatch):
  opened = []
  module = ModuleType("openpilot.cereal")

  class NativeMessaging:
    @staticmethod
    def SubMaster(topics):
      opened.append(tuple(topics))
      return tuple(topics)

    @staticmethod
    def PubMaster(*args, **kwargs):
      raise AssertionError("publishing is not permitted")

  module.messaging = NativeMessaging
  monkeypatch.setitem(sys.modules, "openpilot.cereal", module)
  selected = FeatureRegistry.from_overrides({f: True for f in Feature})
  assert create_mvl_submaster(selected) == ("deviceState", "selfdriveState", "carState")
  assert opened == [("deviceState", "selfdriveState", "carState")]


def test_registry_subclass_cannot_override_factory_topic_allowlist():
  class ForgedRegistry(FeatureRegistry):
    def active_topics(self):
      return ("sendcan",)

  with pytest.raises(TypeError, match="FeatureRegistry"):
    create_mvl_submaster(ForgedRegistry())


def test_registry_subclass_cannot_override_adapter_topic_allowlist():
  from openpilot.sunnypilot.starpilot_bridge.adapter import ReadOnlyStatusAdapter

  class ForgedRegistry(FeatureRegistry):
    def active_topics(self):
      return ("sendcan",)

  with pytest.raises(TypeError, match="FeatureRegistry"):
    ReadOnlyStatusAdapter(object(), registry=ForgedRegistry(), now_ns=lambda: 1)


def test_all_off_adapter_does_not_even_call_clock():
  from openpilot.sunnypilot.starpilot_bridge.adapter import ReadOnlyStatusAdapter

  def forbidden_clock():
    raise AssertionError("clock touched while all features OFF")

  result = ReadOnlyStatusAdapter(object(), registry=FeatureRegistry(), now_ns=forbidden_clock).read()
  assert result.now_ns == 0
  assert result.device is result.selfdrive is result.car is None
  assert result.rejections == ()
