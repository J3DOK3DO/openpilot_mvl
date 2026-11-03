from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, CarStatus, DeviceStatus, SelfdriveStatus
from openpilot.sunnypilot.starpilot_views import Alert, AlertPriority, LayoutKind, Theme, build_presentation


NOW = 10_000_000_000


def snapshot():
  return BridgeSnapshot(NOW, DeviceStatus(True, 50.0, 42.0, NOW - 1), SelfdriveStatus(True, True, NOW - 1), CarStatus(13.5, True, NOW - 1))


def test_all_off_has_no_panels():
  assert build_presentation(BridgeSnapshot(NOW), width=800, height=500).panels == ()


@pytest.mark.parametrize("width,height", [(float("nan"), 600), (800, float("inf")), (0, 600), (800, -1)])
def test_invalid_geometry_fails_closed(width, height):
  output = build_presentation(snapshot(), width=width, height=height)
  assert output.defer_to_mvl and output.panels == () and output.rejection_reasons == ("invalid_input",)


def test_stale_and_malformed_statuses_are_omitted():
  bad = BridgeSnapshot(NOW, DeviceStatus(True, 50.0, 42.0, NOW - 2_000_000_001), None, CarStatus(float("nan"), True, NOW - 1))
  output = build_presentation(bad, width=800, height=600)
  assert output.panels == ()
  assert output.rejection_reasons == ("invalid_device", "invalid_car")


def test_models_are_immutable():
  output = build_presentation(snapshot(), width=1000, height=600)
  with pytest.raises(FrozenInstanceError):
    output.panels[0].value = "changed"
  with pytest.raises(FrozenInstanceError):
    output.panels[0].bounds.width = 1


def test_critical_warning_dominates_by_deferring_everything():
  critical = Alert("OEM", AlertPriority.CRITICAL, "BRAKE")
  output = build_presentation(snapshot(), width=1000, height=600, alerts=(Alert("MVL", AlertPriority.LOW, "note"), critical))
  assert output.defer_to_mvl and output.panels == () and output.overlay == critical and output.protected_alerts == (critical,)


def test_high_warning_is_the_only_overlay_and_does_not_get_suppressed():
  high = Alert("MVL", AlertPriority.HIGH, "Take over")
  output = build_presentation(snapshot(), width=1000, height=600, alerts=(Alert("view", AlertPriority.INFO, "info"), high))
  assert output.defer_to_mvl and output.overlay == high and output.protected_alerts == (high,) and output.panels == ()


def test_all_oem_mvl_high_warnings_are_retained_not_suppressed():
  oem = Alert("OEM", AlertPriority.HIGH, "OEM warning")
  mvl = Alert("MVL", AlertPriority.HIGH, "MVL warning")
  output = build_presentation(snapshot(), width=1000, height=600, alerts=(oem, mvl))
  assert output.protected_alerts == (oem, mvl)


def test_portrait_small_and_large_landscape_select_layouts():
  assert build_presentation(snapshot(), width=600, height=1000).layout is LayoutKind.COMPACT
  assert build_presentation(snapshot(), width=1000, height=600).layout is LayoutKind.FULL


def test_unknown_theme_and_bad_alert_have_deterministic_fallback():
  one = build_presentation(snapshot(), width=800, height=600, theme=object(), alerts=(object(),))
  two = build_presentation(snapshot(), width=800, height=600, theme=object(), alerts=(object(),))
  assert one == two and one.palette == build_presentation(snapshot(), width=800, height=600, theme=Theme.DARK).palette and one.overlay is None


def test_oem_high_preempts_starpilot_visual_status():
  system_warning = Alert("OEM", AlertPriority.HIGH, "Stability system warning")
  output = build_presentation(snapshot(), width=1000, height=600, alerts=(system_warning,))
  assert output.defer_to_mvl and output.panels == ()
  assert output.overlay == system_warning
