"""Injected-source, fail-closed adapter for three MVL status topics.

This module imports only the Python standard library. It does not create a
subscriber, update a subscriber, publish, access Params, or issue I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from math import isfinite
from threading import Lock
from typing import Any

from .features import Feature, FeatureRegistry
from .models import BridgeSnapshot, CarStatus, DeviceStatus, SelfdriveStatus, TopicRejection

_MAX_AGE_NS = 2_000_000_000
_TOPIC_FEATURES = (
  (Feature.DEVICE_STATUS, "deviceState"),
  (Feature.SELFDRIVE_STATUS, "selfdriveState"),
  (Feature.CAR_STATUS, "carState"),
)


class ReadOnlyStatusAdapter:
  """Projects validated snapshots from a caller-owned SubMaster-like source.

  The source is only indexed after its associated registry feature is enabled.
  It must expose mappings ``alive``, ``valid``, and ``logMonoTime`` plus
  ``__getitem__``. ``now_ns`` must be an injected monotonic nanosecond clock.
  """

  def __init__(self, source: Any, *, registry: FeatureRegistry | None = None,
               now_ns: Callable[[], int], max_age_ns: int = _MAX_AGE_NS) -> None:
    if not callable(now_ns):
      raise TypeError("now_ns must be callable")
    if type(max_age_ns) is not int or max_age_ns <= 0:
      raise ValueError("max_age_ns must be a positive int")
    self._source = source
    self._registry = registry if registry is not None else FeatureRegistry()
    if type(self._registry) is not FeatureRegistry:
      raise TypeError("registry must be FeatureRegistry")
    self._now_ns = now_ns
    self._max_age_ns = max_age_ns
    self._last_now_ns: int | None = None
    self._last_timestamp_ns: dict[str, int] = {}
    self._read_lock = Lock()

  def read(self) -> BridgeSnapshot:
    """Return only valid, fresh, monotonically ordered projections.

    Failures are represented as rejection records rather than propagated source
    exceptions. A bad clock produces no accepted topic data.
    """
    active = self._registry.active_topics()
    if not active:
      # No source, native subscriber, or injected clock is used while all OFF.
      return BridgeSnapshot(now_ns=0)
    if not self._read_lock.acquire(blocking=False):
      # A second reader must not race timestamp state or wait on a stalled
      # source. It can retry after the first caller completes.
      return BridgeSnapshot(now_ns=0, rejections=tuple(TopicRejection(topic, "concurrent_read") for topic in active))
    try:
      return self._read_locked(active)
    finally:
      self._read_lock.release()

  def _read_locked(self, active: tuple[str, ...]) -> BridgeSnapshot:
    try:
      now_ns = _timestamp(self._now_ns())
    except Exception:
      return BridgeSnapshot(now_ns=0, rejections=(TopicRejection("clock", "clock_failure"),))
    if self._last_now_ns is not None and now_ns < self._last_now_ns:
      return BridgeSnapshot(now_ns=now_ns, rejections=tuple(TopicRejection(topic, "clock_rollback") for topic in active))
    self._last_now_ns = now_ns

    accepted: dict[str, object] = {}
    rejected: list[TopicRejection] = []
    for feature, topic in _TOPIC_FEATURES:
      if not self._registry.enabled(feature):
        continue
      try:
        status = self._read_topic(topic, now_ns)
        accepted[topic] = _project(topic, status)
        self._last_timestamp_ns[topic] = status[1]
      except _Rejected as exc:
        rejected.append(TopicRejection(topic, exc.reason))
      except Exception:
        rejected.append(TopicRejection(topic, "source_failure"))
    return BridgeSnapshot(
      now_ns=now_ns,
      device=accepted.get("deviceState") if isinstance(accepted.get("deviceState"), DeviceStatus) else None,
      selfdrive=accepted.get("selfdriveState") if isinstance(accepted.get("selfdriveState"), SelfdriveStatus) else None,
      car=accepted.get("carState") if isinstance(accepted.get("carState"), CarStatus) else None,
      rejections=tuple(rejected),
    )

  def _read_topic(self, topic: str, now_ns: int) -> tuple[Any, int]:
    try:
      alive = self._source.alive[topic]
      valid = self._source.valid[topic]
      timestamp_ns = _timestamp(self._source.logMonoTime[topic])
    except _Rejected:
      raise
    except Exception as exc:
      raise _Rejected("missing_topic") from exc
    if alive is not True:
      raise _Rejected("not_alive")
    if valid is not True:
      raise _Rejected("not_valid")
    if timestamp_ns == 0:
      raise _Rejected("invalid_timestamp")
    if timestamp_ns > now_ns:
      raise _Rejected("future_timestamp")
    if now_ns - timestamp_ns > self._max_age_ns:
      raise _Rejected("stale_timestamp")
    previous = self._last_timestamp_ns.get(topic)
    if previous is not None and timestamp_ns <= previous:
      raise _Rejected("out_of_order_timestamp")
    try:
      state = self._source[topic]
    except Exception as exc:
      raise _Rejected("source_failure") from exc
    return state, timestamp_ns


def _project(topic: str, state_and_timestamp: tuple[Any, int]) -> DeviceStatus | SelfdriveStatus | CarStatus:
  state, timestamp_ns = state_and_timestamp
  if topic == "deviceState":
    return DeviceStatus(
      started=_bool_field(state, "started"),
      free_space_percent=_finite_field(state, "freeSpacePercent", 0.0, 100.0),
      max_temp_c=_finite_field(state, "maxTempC", 0.0, 150.0),
      timestamp_ns=timestamp_ns,
    )
  if topic == "selfdriveState":
    return SelfdriveStatus(enabled=_bool_field(state, "enabled"), active=_bool_field(state, "active"), timestamp_ns=timestamp_ns)
  if topic == "carState":
    cruise = _field(state, "cruiseState")
    return CarStatus(v_ego_mps=_finite_field(state, "vEgo", 0.0, 100.0),
                     cruise_enabled=_bool_field(cruise, "enabled"), timestamp_ns=timestamp_ns)
  raise _Rejected("unsupported_topic")


def _field(state: Any, name: str) -> Any:
  try:
    return getattr(state, name)
  except Exception as exc:
    raise _Rejected("malformed_state") from exc


def _bool_field(state: Any, name: str) -> bool:
  value = _field(state, name)
  if type(value) is not bool:
    raise _Rejected("malformed_state")
  return value


def _finite_field(state: Any, name: str, minimum: float, maximum: float) -> float:
  value = _field(state, name)
  if type(value) not in (int, float) or type(value) is bool:
    raise _Rejected("malformed_state")
  result = float(value)
  if not isfinite(result) or not minimum <= result <= maximum:
    raise _Rejected("out_of_range")
  return result


def _timestamp(value: Any) -> int:
  if type(value) is not int or value < 0:
    raise _Rejected("invalid_timestamp")
  return value


class _Rejected(Exception):
  def __init__(self, reason: str) -> None:
    self.reason = reason
