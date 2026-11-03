from __future__ import annotations

import pytest

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, DeviceStatus, SelfdriveStatus
from openpilot.sunnypilot.starpilot_views.offroad import build_offroad_home_presentation

NOW = 10_000_000_000


def snapshot():
  return BridgeSnapshot(NOW, device=DeviceStatus(False, 50.0, 42.0, NOW - 1))


def render(**changes):
  args = dict(width=1200.0, height=800.0, started=False, home_visible=True, update_present=False, alerts_present=False)
  args.update(changes)
  return build_offroad_home_presentation(snapshot(), **args)


def test_only_unblocked_offroad_home_admits_read_only_panel():
  result = render()
  assert not result.defer_to_mvl
  assert tuple(panel.key for panel in result.panels) == ('device',)


@pytest.mark.parametrize('changes,reason', [
  ({'started': True}, 'started'),
  ({'home_visible': False}, 'home_not_visible'),
  ({'update_present': True}, 'update_present'),
  ({'alerts_present': True}, 'alerts_present'),
  ({'started': True, 'alerts_present': True}, 'started'),
  ({'started': 1}, 'invalid_ui_state'),
  ({'alerts_present': None}, 'invalid_ui_state'),
])
def test_all_blocking_or_malformed_states_defer_without_panels(changes, reason):
  result = render(**changes)
  assert result.defer_to_mvl and result.panels == ()
  assert result.rejection_reasons == (reason,)


def test_stale_snapshot_is_rejected_after_ui_gate():
  stale = BridgeSnapshot(NOW, device=DeviceStatus(False, 50.0, 42.0, NOW - 2_000_000_001))
  result = build_offroad_home_presentation(stale, width=1200.0, height=800.0, started=False,
                                            home_visible=True, update_present=False, alerts_present=False)
  assert result.panels == () and result.rejection_reasons == ('invalid_device',)


@pytest.mark.parametrize('contradiction,reason', [
  (BridgeSnapshot(NOW, device=DeviceStatus(True, 50.0, 42.0, NOW - 1)), 'snapshot_started'),
  (BridgeSnapshot(NOW, selfdrive=SelfdriveStatus(True, True, NOW - 1)), 'snapshot_active'),
  (BridgeSnapshot(NOW, device=DeviceStatus(1, 50.0, 42.0, NOW - 1)), 'invalid_device_started'),
])
def test_conflicting_snapshot_state_never_admits_panel(contradiction, reason):
  result = build_offroad_home_presentation(contradiction, width=1200.0, height=800.0, started=False,
                                            home_visible=True, update_present=False, alerts_present=False)
  assert result.defer_to_mvl and result.panels == () and result.rejection_reasons == (reason,)
