"""Conservative, renderer-neutral admission policy for optional offroad status.

A native UI must supply these flags from its own state. This module neither
subscribes to IPC nor registers a widget or a vehicle-facing process.
"""

from __future__ import annotations

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, DeviceStatus, SelfdriveStatus

from .models import LayoutKind, PALETTES, Presentation, Theme
from .presentation import build_presentation


def build_offroad_home_presentation(
  snapshot: BridgeSnapshot,
  *,
  width: float,
  height: float,
  started: bool,
  home_visible: bool,
  update_present: bool,
  alerts_present: bool,
  theme: Theme = Theme.DARK,
) -> Presentation:
  """Admit optional panels only on an unblocked offroad HOME view.

  Unknown or malformed UI state is treated as blocked. The caller must also
  preserve native MVL/OEM alert rendering; this result never replaces it.
  """
  flags = (started, home_visible, update_present, alerts_present)
  if any(type(flag) is not bool for flag in flags):
    return _deferred("invalid_ui_state")
  if started:
    return _deferred("started")
  if not home_visible:
    return _deferred("home_not_visible")
  if update_present:
    return _deferred("update_present")
  if alerts_present:
    return _deferred("alerts_present")
  if type(snapshot) is not BridgeSnapshot:
    return _deferred("invalid_snapshot")
  if snapshot.device is not None:
    if type(snapshot.device) is not DeviceStatus or type(snapshot.device.started) is not bool:
      return _deferred("invalid_device_started")
    if snapshot.device.started:
      return _deferred("snapshot_started")
  if snapshot.selfdrive is not None:
    if type(snapshot.selfdrive) is not SelfdriveStatus or type(snapshot.selfdrive.active) is not bool:
      return _deferred("invalid_selfdrive_active")
    if snapshot.selfdrive.active:
      return _deferred("snapshot_active")
  return build_presentation(snapshot, width=width, height=height, theme=theme)


def _deferred(reason: str) -> Presentation:
  return Presentation(LayoutKind.COMPACT, PALETTES[Theme.DARK], (), None, (), True, (reason,))
