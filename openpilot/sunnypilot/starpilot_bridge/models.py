"""Immutable data-only projections and failure descriptions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceStatus:
  """Native deviceState projection; percent is [0, 100], temperature is degC."""

  started: bool
  free_space_percent: float
  max_temp_c: float
  timestamp_ns: int


@dataclass(frozen=True)
class SelfdriveStatus:
  """Native selfdriveState projection."""

  enabled: bool
  active: bool
  timestamp_ns: int


@dataclass(frozen=True)
class CarStatus:
  """Native carState projection; v_ego_mps is metres per second."""

  v_ego_mps: float
  cruise_enabled: bool
  timestamp_ns: int


@dataclass(frozen=True)
class TopicRejection:
  """A fail-closed reason. No source object or exception is retained."""

  topic: str
  reason: str


@dataclass(frozen=True)
class BridgeSnapshot:
  """A single immutable read result; omitted status fields were not accepted."""

  now_ns: int
  device: DeviceStatus | None = None
  selfdrive: SelfdriveStatus | None = None
  car: CarStatus | None = None
  rejections: tuple[TopicRejection, ...] = ()
