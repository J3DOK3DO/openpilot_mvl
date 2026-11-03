"""M0--M3 read-only conversion from the pinned bridge schema to view models.

M0 accepts only :class:`BridgeSnapshot`; M1 validates its accepted projections;
M2 selects bounded geometry; M3 composes immutable renderer-neutral panels.
"""

from __future__ import annotations

import math

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, CarStatus, DeviceStatus, SelfdriveStatus

from .models import Alert, AlertPriority, LayoutKind, PALETTES, Palette, Presentation, Rect, StatusPanel, Theme

_MAX_AGE_NS = 2_000_000_000
_MIN_DIMENSION = 1.0
_MAX_DIMENSION = 16_384.0
_FULL_MIN_WIDTH = 900.0


def _finite(value: object, minimum: float, maximum: float) -> bool:
  return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def _fresh(snapshot: BridgeSnapshot, timestamp_ns: object) -> bool:
  return type(snapshot.now_ns) is int and type(timestamp_ns) is int and 0 <= snapshot.now_ns - timestamp_ns <= _MAX_AGE_NS


def _valid_device(snapshot: BridgeSnapshot, value: DeviceStatus) -> bool:
  return type(value.started) is bool and _finite(value.free_space_percent, 0, 100) and _finite(value.max_temp_c, -40, 150) and _fresh(snapshot, value.timestamp_ns)


def _valid_selfdrive(snapshot: BridgeSnapshot, value: SelfdriveStatus) -> bool:
  return type(value.enabled) is bool and type(value.active) is bool and _fresh(snapshot, value.timestamp_ns)


def _valid_car(snapshot: BridgeSnapshot, value: CarStatus) -> bool:
  return type(value.cruise_enabled) is bool and _finite(value.v_ego_mps, 0, 100) and _fresh(snapshot, value.timestamp_ns)


def _layout(width: object, height: object) -> LayoutKind | None:
  if not _finite(width, _MIN_DIMENSION, _MAX_DIMENSION) or not _finite(height, _MIN_DIMENSION, _MAX_DIMENSION):
    return None
  return LayoutKind.FULL if width >= _FULL_MIN_WIDTH and width >= height else LayoutKind.COMPACT


def _overlay(alerts: tuple[Alert, ...]) -> Alert | None:
  # Stable max keeps input order as the deterministic tiebreaker.
  valid = tuple(item for item in alerts if isinstance(item, Alert) and isinstance(item.priority, AlertPriority) and bool(item.message))
  return max(valid, key=lambda item: item.priority.value, default=None)


def _protected(alerts: tuple[Alert, ...]) -> tuple[Alert, ...]:
  """Retain every OEM/MVL high/critical warning, never merely the winner."""
  return tuple(item for item in alerts if isinstance(item, Alert) and item.source in ("OEM", "MVL") and item.priority in (AlertPriority.HIGH, AlertPriority.CRITICAL) and bool(item.message))


def build_presentation(snapshot: BridgeSnapshot, *, width: float, height: float, theme: Theme = Theme.DARK, alerts: tuple[Alert, ...] = ()) -> Presentation:
  """Return a pure view model; invalid inputs yield a deterministic empty model.

  A critical OEM/MVL (or any) alert defers entirely, so status panels cannot
  obscure it. A high alert remains the sole overlay above all generated panels.
  """
  palette: Palette = PALETTES.get(theme, PALETTES[Theme.DARK])
  layout = _layout(width, height)
  if not isinstance(snapshot, BridgeSnapshot) or layout is None:
    return Presentation(LayoutKind.COMPACT, palette, (), None, (), True, ("invalid_input",))
  selected = _overlay(alerts)
  protected = _protected(alerts)
  # OEM/MVL high and critical alerts preempt *all* optional StarPilot panels.
  # Status UI never gets to choose an overlay over a factory/system warning.
  if protected:
    dominant = max(protected, key=lambda item: item.priority.value)
    return Presentation(layout, palette, (), dominant, protected, True, ("protected_mvl_oem_alert",))
  if selected is not None and selected.priority is AlertPriority.CRITICAL:
    return Presentation(layout, palette, (), selected, protected, True, ("critical_alert",))
  panels: list[StatusPanel] = []
  rejected: list[str] = []
  panel_width = width - 32.0 if layout is LayoutKind.COMPACT else (width - 48.0) / 3.0
  panel_height = 70.0
  candidates = (
    ("device", snapshot.device, _valid_device),
    ("selfdrive", snapshot.selfdrive, _valid_selfdrive),
    ("car", snapshot.car, _valid_car),
  )
  for index, (key, status, validator) in enumerate(candidates):
    if status is None:
      continue
    if not validator(snapshot, status):
      rejected.append(f"invalid_{key}")
      continue
    if key == "device":
      title, value = "DEVICE", f"{status.max_temp_c:.0f}°C · {status.free_space_percent:.0f}% free"
    elif key == "selfdrive":
      title, value = "SELFDRIVE", "ACTIVE" if status.active else "ENABLED" if status.enabled else "OFF"
    else:
      title, value = "VEHICLE", f"{status.v_ego_mps * 3.6:.0f} km/h · {'CRUISE' if status.cruise_enabled else 'MANUAL'}"
    x = 16.0 if layout is LayoutKind.COMPACT else 16.0 + index * (panel_width + 8.0)
    y = 16.0 + index * 78.0 if layout is LayoutKind.COMPACT else 16.0
    panels.append(StatusPanel(key, title, value, Rect(x, y, panel_width, panel_height)))
  return Presentation(layout, palette, tuple(panels), selected, protected, False, tuple(rejected))
