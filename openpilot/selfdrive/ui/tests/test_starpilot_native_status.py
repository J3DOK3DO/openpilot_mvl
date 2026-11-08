"""Host proof for the optional MVL raylib offroad status seam."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

rl = pytest.importorskip("pyray")

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, DeviceStatus
from openpilot.selfdrive.ui.layouts.home import HomeLayoutState
from openpilot.selfdrive.ui.sunnypilot.layouts import home as native_home


NOW = 10_000_000_000


def _layout(monkeypatch):
  layout = native_home.HomeLayoutSP.__new__(native_home.HomeLayoutSP)
  layout._is_visible = True
  layout.header_rect = rl.Rectangle(40, 40, 1000, 80)
  layout.current_state = HomeLayoutState.HOME
  layout.update_available = False
  layout.alert_count = 0
  layout._status_snapshot_supplier = None
  monkeypatch.setattr(native_home.ui_state, "started", False)
  monkeypatch.setattr(native_home.time, "monotonic_ns", lambda: NOW)
  drawn = []
  labels = []
  monkeypatch.setattr(native_home.rl, "draw_rectangle_rounded", lambda *args: drawn.append(args))
  monkeypatch.setattr(native_home, "gui_label", lambda *args, **kwargs: labels.append((args, kwargs)))
  return layout, drawn, labels


def _snapshot(*, started=False):
  return BridgeSnapshot(NOW, device=DeviceStatus(started, 50.0, 42.0, NOW - 1))


def test_native_status_is_default_off(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout._render_status_badge(800)
  assert drawn == labels == []


def test_hidden_home_never_reads_optional_status_source(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout._is_visible = False
  calls = []
  layout.set_status_snapshot_supplier(lambda: calls.append(True))
  layout._render_status_badge(800)
  assert calls == drawn == labels == []


def test_native_status_draws_fresh_read_only_device_without_brand_overlap(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout.set_status_snapshot_supplier(_snapshot)
  layout._render_status_badge(800)
  assert len(drawn) == len(labels) == 1
  badge = drawn[0][0]
  assert badge.x == layout.header_rect.x
  assert badge.x + badge.width < 800
  assert "DEVICE: 42°C · 50% free" == labels[0][0][1]


def test_real_mvl_header_invokes_optional_status_seam(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout.params = SimpleNamespace(get=lambda _: None)
  layout.set_status_snapshot_supplier(_snapshot)
  monkeypatch.setattr(native_home.gui_app, "font", lambda _: object())
  monkeypatch.setattr(native_home, "measure_text_cached", lambda *args: rl.Vector2(200, 40))
  layout._render_header()
  assert len(drawn) == 1
  assert [call[0][1] for call in labels] == ["sunnypilot", "DEVICE: 42°C · 50% free"]


@pytest.mark.parametrize("change", [
  {"current_state": HomeLayoutState.UPDATE},
  {"current_state": HomeLayoutState.ALERTS},
  {"update_available": True},
  {"alert_count": 1},
])
def test_native_update_and_alert_priority_never_calls_status_source(monkeypatch, change):
  layout, drawn, labels = _layout(monkeypatch)
  for key, value in change.items():
    setattr(layout, key, value)
  called = []
  layout.set_status_snapshot_supplier(lambda: called.append(True))
  layout._render_status_badge(800)
  assert called == drawn == labels == []


def test_native_onroad_and_snapshot_disagreement_fail_closed(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout.set_status_snapshot_supplier(lambda: _snapshot(started=True))
  layout._render_status_badge(800)
  assert drawn == labels == []
  layout.set_status_snapshot_supplier(_snapshot)
  monkeypatch.setattr(native_home.ui_state, "started", True)
  layout._render_status_badge(800)
  assert drawn == labels == []


def test_native_small_header_and_source_failure_restore_original_header(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout.set_status_snapshot_supplier(_snapshot)
  layout._render_status_badge(300)
  assert drawn == labels == []
  layout.set_status_snapshot_supplier(lambda: 1 / 0)
  layout._render_status_badge(800)
  assert drawn == labels == []
  layout.set_status_snapshot_supplier(lambda: object())
  layout._render_status_badge(800)
  assert drawn == labels == []
  layout.set_status_snapshot_supplier(lambda: BridgeSnapshot(NOW, car=object()))
  layout._render_status_badge(800)
  assert drawn == labels == []


@pytest.mark.parametrize("snapshot_time_ns", [NOW - 2_000_000_001, NOW + 1, True, "old"])
def test_cached_or_invalid_snapshot_time_restores_original_header(monkeypatch, snapshot_time_ns):
  layout, drawn, labels = _layout(monkeypatch)
  layout.set_status_snapshot_supplier(lambda: BridgeSnapshot(snapshot_time_ns,
    device=DeviceStatus(False, 50.0, 42.0, snapshot_time_ns - 1 if type(snapshot_time_ns) is int else NOW - 1)))
  layout._render_status_badge(800)
  assert drawn == labels == []


def test_snapshot_age_boundary_is_admitted(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout.set_status_snapshot_supplier(lambda: BridgeSnapshot(NOW - 2_000_000_000,
    device=DeviceStatus(False, 50.0, 42.0, NOW - 2_000_000_000)))
  layout._render_status_badge(800)
  assert len(drawn) == len(labels) == 1


def test_cached_topic_inside_recent_snapshot_restores_original_header(monkeypatch):
  layout, drawn, labels = _layout(monkeypatch)
  layout.params = SimpleNamespace(get=lambda _: None)
  layout.set_status_snapshot_supplier(lambda: BridgeSnapshot(NOW - 1,
    device=DeviceStatus(False, 50.0, 42.0, NOW - 2_000_000_001)))
  monkeypatch.setattr(native_home.gui_app, "font", lambda _: object())
  monkeypatch.setattr(native_home, "measure_text_cached", lambda *args: rl.Vector2(200, 40))
  layout._render_header()
  assert drawn == []
  assert [call[0][1] for call in labels] == ["sunnypilot"]
