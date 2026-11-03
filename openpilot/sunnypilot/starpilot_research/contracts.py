"""One-way adapter from the pinned M0–M3 immutable bridge projection.

This module consumes only bridge data models. It neither constructs the bridge
adapter nor accesses a subscriber, preserving the caller-owned read boundary.
"""

from __future__ import annotations

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot

from .models import NativeMvlStatus


def native_status_from_m0_m3(snapshot: BridgeSnapshot) -> NativeMvlStatus:
  """Turn an accepted M0–M3 snapshot into conservative status evidence.

  A missing projection is never fabricated: it is represented as both not
  fresh and not valid. The original `TopicRejection` remains in the bridge;
  this reduced research contract only supplies fail-closed booleans.
  """
  if type(snapshot) is not BridgeSnapshot:
    raise TypeError("snapshot must be the pinned M0–M3 BridgeSnapshot")
  device_ok = snapshot.device is not None
  selfdrive_ok = snapshot.selfdrive is not None
  car_ok = snapshot.car is not None
  return NativeMvlStatus(
    bridge_present=True,
    device_fresh=device_ok,
    selfdrive_fresh=selfdrive_ok,
    car_fresh=car_ok,
    device_valid=device_ok,
    selfdrive_valid=selfdrive_ok,
    car_valid=car_ok,
    selfdrive_active=snapshot.selfdrive.active if selfdrive_ok else False,
    cruise_enabled=snapshot.car.cruise_enabled if car_ok else False,
  )
