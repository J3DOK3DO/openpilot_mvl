from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, CarStatus, DeviceStatus, SelfdriveStatus
from openpilot.sunnypilot.starpilot_galaxy import GalaxyHandler, GalaxyRequest, GalaxySettings, SettingsError
from openpilot.sunnypilot.starpilot_models.catalog import ModelCatalog, ModelEntry


NOW = 10_000_000_000
TOKEN = "offline-test-token"


def snapshot() -> BridgeSnapshot:
  return BridgeSnapshot(
    now_ns=NOW,
    device=DeviceStatus(True, 55.5, 41.0, NOW - 1),
    selfdrive=SelfdriveStatus(False, False, NOW - 2),
    car=CarStatus(12.5, True, NOW - 3),
  )


def handler(provider=lambda: snapshot(), **settings):
  return GalaxyHandler(GalaxySettings(enabled=True, token=TOKEN, **settings), provider, lambda: NOW)


def request(path="/api/v1/status", token=TOKEN, **kwargs):
  headers = {"X-Galaxy-Token": token} if token is not None else {}
  return GalaxyRequest("GET", path, headers, **kwargs)


def test_default_off_and_no_provider_access():
  calls = 0
  def provider():
    nonlocal calls
    calls += 1
    raise AssertionError("must not run")
  api = GalaxyHandler(GalaxySettings(enabled=False, token=TOKEN), provider, lambda: NOW)
  response = api.handle(request())
  assert (response.status, response.json(), calls) == (403, {"error": "disabled"}, 0)


@pytest.mark.parametrize("value", ["true", 1, None])
def test_invalid_settings(value):
  with pytest.raises(SettingsError):
    GalaxySettings(enabled=value, token=TOKEN)
  with pytest.raises(SettingsError):
    GalaxySettings(enabled=True, token="")
  with pytest.raises(SettingsError):
    GalaxySettings(enabled=True, token=TOKEN, max_snapshot_age_ns=0)


@pytest.mark.parametrize("bad_token", [None, "wrong", ""])
def test_missing_or_wrong_auth_is_unauthorized(bad_token):
  response = handler().handle(request(token=bad_token))
  assert response.status == 401
  assert response.json() == {"error": "unauthorized"}
  assert TOKEN.encode() not in response.body


@pytest.mark.parametrize("method", ["POST", "PATCH", "HEAD", "DELETE"])
def test_non_get_methods_are_denied(method):
  response = handler().handle(GalaxyRequest(method, "/api/v1/status", {"X-Galaxy-Token": TOKEN}))
  assert response.status == 405
  assert response.headers["Allow"] == "GET"


def test_unknown_route_and_body_or_header_rejection():
  assert handler().handle(request("/unknown")).status == 404
  assert handler().handle(request(body=b'{"ignored":false}')).status == 400
  assert handler().handle(GalaxyRequest("GET", "/api/v1/status", {"X-Galaxy-Token": TOKEN, "x": "a" * 4096})).status == 400
  assert handler().handle(GalaxyRequest("GET", "/api/v1/status", {"X-Galaxy-Token": 1})).status == 400


def test_allowlisted_status_and_security_headers_only():
  response = handler().handle(request())
  assert response.status == 200
  assert response.headers["Cache-Control"] == "no-cache, no-store"
  assert response.headers["X-Content-Type-Options"] == "nosniff"
  assert response.json() == {
    "snapshot_time_ns": NOW,
    "device": {"started": True, "free_space_percent": 55.5, "max_temp_c": 41.0},
    "selfdrive": {"enabled": False, "active": False},
    "car": {"v_ego_mps": 12.5, "cruise_enabled": True},
  }
  rendered = response.body.decode()
  for forbidden in ("vin", "location", "latitude", "longitude", "telemetry", TOKEN):
    assert forbidden not in rendered


def test_health_and_models_are_static_and_never_call_provider():
  api = handler(lambda: (_ for _ in ()).throw(AssertionError("not needed")))
  assert api.handle(request("/api/v1/health")).json() == {"status": "ok"}
  assert api.handle(request("/api/v1/models")).json() == {"models": []}


def test_explicit_read_only_model_metadata_and_default_off():
  entry = ModelEntry("sample", "Sample", "1", "a" * 64, 7, "aarch64", ("tinygrad",))
  calls = 0
  def models():
    nonlocal calls
    calls += 1
    return ModelCatalog((entry,))
  disabled = GalaxyHandler(GalaxySettings(), lambda: snapshot(), lambda: NOW, models)
  assert disabled.handle(request("/api/v1/models")).status == 403
  assert calls == 0
  api = GalaxyHandler(GalaxySettings(enabled=True, token=TOKEN), lambda: snapshot(), lambda: NOW, models)
  assert api.handle(request("/api/v1/models", token="wrong")).status == 401
  assert calls == 0
  response = api.handle(request("/api/v1/models"))
  assert response.status == 200
  assert response.json() == {"models": [{"id": "sample", "name": "Sample", "version": "1", "target_abi": "aarch64", "expected_runtimes": ["tinygrad"]}]}
  assert calls == 1
  assert b"sha256" not in response.body and b"size" not in response.body


def test_bad_model_provider_fails_closed_without_details():
  def failed():
    raise RuntimeError("private model path")
  bad_entry = ModelEntry("/private/path", "name", "1", "a" * 64, 1, "unsupported-abi", ("unapproved-runtime",))
  duplicate = ModelEntry("same", "name", "1", "a" * 64, 1, "aarch64", ("tinygrad",))
  oversized = ModelEntry("x" * 1_000_000, "name", "1", "a" * 64, 1, "aarch64", ("tinygrad",))
  for provider in (failed, lambda: object(), lambda: ModelCatalog((object(),)),
                   lambda: ModelCatalog((bad_entry,)), lambda: ModelCatalog((duplicate, duplicate)),
                   lambda: ModelCatalog((oversized,))):
    api = GalaxyHandler(GalaxySettings(enabled=True, token=TOKEN), lambda: snapshot(), lambda: NOW, provider)
    response = api.handle(request("/api/v1/models"))
    assert (response.status, response.json()) == (503, {"error": "models_unavailable"})
    assert b"private" not in response.body


@pytest.mark.parametrize("provider", [
  lambda: None,
  lambda: object(),
  lambda: BridgeSnapshot(now_ns=NOW),
  lambda: snapshot().__class__(now_ns=NOW, car=CarStatus(1.0, True, NOW - 3_000_000_000)),
])
def test_unavailable_or_stale_snapshot_is_generic_503(provider):
  response = handler(provider).handle(request())
  assert (response.status, response.json()) == (503, {"error": "snapshot_unavailable"})


def test_provider_failure_and_unexpected_values_are_generic_503():
  def failing():
    raise RuntimeError("secret provider detail")
  bad = BridgeSnapshot(now_ns=NOW, car=CarStatus(float("nan"), True, NOW))
  for provider in (failing, lambda: bad):
    response = handler(provider).handle(request())
    assert response.status == 503
    assert b"secret" not in response.body


def test_snapshot_is_not_mutated_and_is_frozen():
  value = snapshot()
  with pytest.raises(FrozenInstanceError):
    value.now_ns = 1
  before = repr(value)
  assert handler(lambda: value).handle(request()).status == 200
  assert repr(value) == before


def test_source_has_no_network_params_or_file_reads():
  source = Path(__file__).parents[1] / "core.py"
  text = source.read_text(encoding="utf-8")
  for forbidden in ("import socket", "from socket", "Params", ".put(", "open(", "sendcan", "PubMaster"):
    assert forbidden not in text


def test_disabled_settings_are_constructible_without_a_secret():
  api = GalaxyHandler(GalaxySettings(), lambda: (_ for _ in ()).throw(AssertionError("provider accessed")), lambda: (_ for _ in ()).throw(AssertionError("clock accessed")))
  response = api.handle(GalaxyRequest(method="GET", path="/api/v1/status", headers={}))
  assert response.status == 403
  assert response.json()["error"] == "disabled"
