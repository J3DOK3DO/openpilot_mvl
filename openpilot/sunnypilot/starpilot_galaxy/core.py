"""Fail-closed, transport-neutral Galaxy read-only request handler.

It deliberately contains no WSGI/ASGI adapter and no socket imports.  A host
application must explicitly construct it with a snapshot provider; doing so
does not make this package a deployed or authenticated network service.
"""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import json
from typing import Callable, Mapping

from openpilot.sunnypilot.starpilot_bridge.models import (
  BridgeSnapshot,
  CarStatus,
  DeviceStatus,
  SelfdriveStatus,
)
from openpilot.sunnypilot.starpilot_models.catalog import DEFAULT_CATALOG, ModelCatalog, ModelEntry, parse_catalog


_MAX_HEADER_BYTES = 4096
_JSON_HEADERS = {
  "Cache-Control": "no-cache, no-store",
  "Content-Type": "application/json; charset=utf-8",
  "X-Content-Type-Options": "nosniff",
}
_METHODS = {"GET"}
_ROUTES = {"/api/v1/health", "/api/v1/status", "/api/v1/models"}


class SettingsError(ValueError):
  """Raised before handler creation when a security setting is invalid."""


@dataclass(frozen=True)
class GalaxySettings:
  """Explicit, host-supplied settings; disabled is the only default."""

  enabled: bool = False
  token: str = ""
  max_snapshot_age_ns: int = 2_000_000_000

  def __post_init__(self) -> None:
    if type(self.enabled) is not bool:
      raise SettingsError("enabled must be bool")
    if type(self.token) is not str or (self.enabled and not self.token):
      raise SettingsError("enabled Galaxy requires a nonempty text secret")
    if type(self.max_snapshot_age_ns) is not int or self.max_snapshot_age_ns <= 0:
      raise SettingsError("max_snapshot_age_ns must be a positive int")


@dataclass(frozen=True)
class GalaxyRequest:
  """A normalized request supplied by a future, separately reviewed adapter."""

  method: str
  path: str
  headers: Mapping[str, str]
  body: bytes = b""


@dataclass(frozen=True)
class GalaxyResponse:
  status: int
  headers: Mapping[str, str]
  body: bytes

  def json(self) -> dict[str, object]:
    """Test convenience only; production adapters should forward ``body``."""
    return json.loads(self.body.decode("utf-8"))


class GalaxyHandler:
  """An explicit, side-effect-free dispatcher over immutable bridge snapshots."""

  def __init__(
    self,
    settings: GalaxySettings,
    snapshot_provider: Callable[[], BridgeSnapshot],
    now_ns: Callable[[], int],
    models_provider: Callable[[], ModelCatalog] | None = None,
  ) -> None:
    if type(settings) is not GalaxySettings:
      raise SettingsError("settings must be GalaxySettings")
    if not callable(snapshot_provider) or not callable(now_ns):
      raise TypeError("provider and clock must be callable")
    self._settings = settings
    self._snapshot_provider = snapshot_provider
    self._now_ns = now_ns
    if models_provider is not None and not callable(models_provider):
      raise TypeError("models provider must be callable")
    self._models_provider = models_provider or (lambda: DEFAULT_CATALOG)

  def handle(self, request: GalaxyRequest) -> GalaxyResponse:
    """Return a generic, cache-forbidden response; never raises provider data."""
    if type(request) is not GalaxyRequest:
      return self._error(400, "invalid_request")
    if not self._valid_request_shape(request):
      return self._error(400, "invalid_request")
    if request.method not in _METHODS:
      return self._error(405, "method_not_allowed", {"Allow": "GET"})
    if request.path not in _ROUTES:
      return self._error(404, "not_found")
    if not self._settings.enabled:
      return self._error(403, "disabled")
    supplied = request.headers.get("X-Galaxy-Token")
    if type(supplied) is not str:
      return self._error(401, "unauthorized", {"WWW-Authenticate": "Bearer"})
    # Both operands are validated, exact text values. compare_digest avoids an
    # early-exit comparison of the secret itself.
    if not hmac.compare_digest(supplied, self._settings.token):
      return self._error(401, "unauthorized", {"WWW-Authenticate": "Bearer"})
    if request.path == "/api/v1/health":
      return self._json(200, {"status": "ok"})
    if request.path == "/api/v1/models":
      try:
        return self._json(200, _safe_models_payload(self._models_provider()))
      except Exception:
        return self._error(503, "models_unavailable")
    return self._status()

  def _valid_request_shape(self, request: GalaxyRequest) -> bool:
    if type(request.method) is not str or type(request.path) is not str:
      return False
    if type(request.body) is not bytes or request.body:
      return False
    if not isinstance(request.headers, Mapping):
      return False
    total = 0
    try:
      for name, value in request.headers.items():
        if type(name) is not str or type(value) is not str:
          return False
        total += len(name.encode("utf-8")) + len(value.encode("utf-8"))
        if total > _MAX_HEADER_BYTES:
          return False
    except (AttributeError, UnicodeError, TypeError):
      return False
    return True

  def _status(self) -> GalaxyResponse:
    try:
      snapshot = self._snapshot_provider()
      now_ns = self._now_ns()
      payload = _safe_status_payload(snapshot, now_ns, self._settings.max_snapshot_age_ns)
    except Exception:
      # Never expose provider/clock errors, objects, or a partial snapshot.
      return self._error(503, "snapshot_unavailable")
    return self._json(200, payload)

  @staticmethod
  def _json(status: int, payload: dict[str, object], extra: Mapping[str, str] | None = None) -> GalaxyResponse:
    headers = dict(_JSON_HEADERS)
    if extra:
      headers.update(extra)
    return GalaxyResponse(status, headers, json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8"))

  @classmethod
  def _error(cls, status: int, code: str, extra: Mapping[str, str] | None = None) -> GalaxyResponse:
    return cls._json(status, {"error": code}, extra)


def _safe_status_payload(snapshot: object, now_ns: object, max_age_ns: int) -> dict[str, object]:
  """Validate every serialized value, then emit only the documented allowlist."""
  if type(snapshot) is not BridgeSnapshot or type(now_ns) is not int or now_ns < 0:
    raise ValueError("invalid snapshot")
  if type(snapshot.now_ns) is not int or snapshot.now_ns < 0:
    raise ValueError("invalid snapshot time")
  statuses = (snapshot.device, snapshot.selfdrive, snapshot.car)
  if not any(value is not None for value in statuses):
    raise ValueError("empty snapshot")
  payload: dict[str, object] = {"snapshot_time_ns": snapshot.now_ns}
  if snapshot.device is not None:
    value = snapshot.device
    if type(value) is not DeviceStatus or type(value.started) is not bool or not _finite(value.free_space_percent, 0, 100) or not _finite(value.max_temp_c, 0, 150):
      raise ValueError("invalid device")
    _fresh(value.timestamp_ns, now_ns, max_age_ns)
    payload["device"] = {"started": value.started, "free_space_percent": value.free_space_percent, "max_temp_c": value.max_temp_c}
  if snapshot.selfdrive is not None:
    value = snapshot.selfdrive
    if type(value) is not SelfdriveStatus or type(value.enabled) is not bool or type(value.active) is not bool:
      raise ValueError("invalid selfdrive")
    _fresh(value.timestamp_ns, now_ns, max_age_ns)
    payload["selfdrive"] = {"enabled": value.enabled, "active": value.active}
  if snapshot.car is not None:
    value = snapshot.car
    if type(value) is not CarStatus or type(value.cruise_enabled) is not bool or not _finite(value.v_ego_mps, 0, 100):
      raise ValueError("invalid car")
    _fresh(value.timestamp_ns, now_ns, max_age_ns)
    payload["car"] = {"v_ego_mps": value.v_ego_mps, "cruise_enabled": value.cruise_enabled}
  return payload


def _safe_models_payload(catalog: object) -> dict[str, object]:
  """Expose bounded, non-executable metadata from an explicitly injected catalog."""
  if type(catalog) is not ModelCatalog or len(catalog.entries) > 128:
    raise ValueError("invalid catalog")
  raw_entries = []
  for entry in catalog.entries:
    if type(entry) is not ModelEntry:
      raise ValueError("invalid model entry")
    strings = (entry.model_id, entry.name, entry.version, entry.sha256, entry.target_abi)
    if any(type(value) is not str or len(value) > 128 for value in strings):
      raise ValueError("invalid model metadata length")
    if type(entry.size) is not int or not 0 <= entry.size <= 2 * 1024 * 1024 * 1024:
      raise ValueError("invalid model size")
    if type(entry.expected_runtimes) is not tuple or len(entry.expected_runtimes) > 8 or any(type(value) is not str or len(value) > 128 for value in entry.expected_runtimes):
      raise ValueError("invalid model runtimes")
    raw_entries.append({"id": entry.model_id, "name": entry.name, "version": entry.version, "sha256": entry.sha256,
                        "size": entry.size, "target_abi": entry.target_abi, "expected_runtimes": entry.expected_runtimes})
  # The immutable dataclass can be constructed directly. Reuse the catalog
  # parser's full allowlist, size bounds, and unique-ID checks at this boundary.
  validated = parse_catalog(json.dumps({"models": raw_entries}, allow_nan=False))
  return {"models": [{"id": entry.model_id, "name": entry.name, "version": entry.version,
                      "target_abi": entry.target_abi, "expected_runtimes": list(entry.expected_runtimes)}
                     for entry in validated.entries]}


def _finite(value: object, low: float, high: float) -> bool:
  return type(value) is float and value == value and value not in (float("inf"), float("-inf")) and low <= value <= high


def _fresh(timestamp_ns: object, now_ns: int, max_age_ns: int) -> None:
  if type(timestamp_ns) is not int or timestamp_ns < 0 or timestamp_ns > now_ns or now_ns - timestamp_ns > max_age_ns:
    raise ValueError("stale status")
