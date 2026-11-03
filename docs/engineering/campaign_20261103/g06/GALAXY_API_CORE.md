# G06 Galaxy API core — offline host prototype

## Status and boundary

**PASS: isolated host unit-test scope. HOLD: vehicle, runtime, and network deployment.**

This adds `openpilot/sunnypilot/starpilot_galaxy/`, a pure-Python, transport-neutral request handler. It is **not** a daemon, listener, WSGI/ASGI integration, startup registration, deployed service, or an authenticated network service. No production code calls it. A transport adapter needs a separate design, threat review, and qualification gate.

It is for the 2025 US Honda Accord 11G Hybrid Bosch-C/CAN-FD context, but has no actual-car interface. MVL remains the sole vehicle-control owner. This package has no control path and does not import Panda, opendbc, Honda control, UDS, CAN, or Dom driving-control code. Verified starting point: `f19b4ea0dfd0f3e3ab2537dba2d0bfb863760ed0`. No commit or push was made.

## Data contract and routes

The handler accepts an injected zero-argument provider returning the immutable M0–M3 `BridgeSnapshot` from `openpilot.sunnypilot.starpilot_bridge.models`. It imports no adapter/factory and never reads IPC itself. It re-validates exact snapshot/status classes, finite bounded values, and every included timestamp using an injected clock. Missing, stale, future, malformed, empty, or provider-failing data returns generic `503 {"error":"snapshot_unavailable"}`.

`GalaxySettings` is explicit and strict: `enabled` defaults to `False`; a non-empty text token and positive integer freshness duration are mandatory even while disabled. There is no environment, Params, file, or network configuration input.

| Method | Path | Result |
|---|---|---|
| `GET` | `/api/v1/health` | Authenticated static `{"status":"ok"}` |
| `GET` | `/api/v1/models` | Authenticated placeholder `{"models":[]}` |
| `GET` | `/api/v1/status` | Authenticated allowlisted M0–M3 status projection |

All other methods (including `HEAD`, `POST`, and `PATCH`) return 405 with `Allow: GET`; unknown paths return 404. Invalid request shape, non-empty body, or headers exceeding 4096 UTF-8 bytes return 400. Disabled returns 403. Missing/wrong token returns 401. Token verification uses `hmac.compare_digest` on validated non-empty text values. Every response has `Cache-Control: no-cache, no-store`, `Content-Type: application/json; charset=utf-8`, and `X-Content-Type-Options: nosniff`.

The body is accepted only when exactly empty `bytes`; JSON is never parsed or interpreted. Status output is restricted to snapshot time and the M0–M3 documented device (`started`, free space, max temperature), selfdrive (`enabled`, `active`), and car (speed, cruise-enabled) fields. It excludes VIN, identity, location, raw telemetry, provider exceptions, rejections, settings, token, and any secret.

## Threat model

| Threat | Control / residual boundary |
|---|---|
| Accidental enablement | Default-off setting; strict constructor validation; no production registration. |
| Token guessing/timing | Mandatory non-empty exact text secret and `hmac.compare_digest`; TLS/rate limiting are outside this non-network core. |
| Route/method expansion | Fixed route and GET allowlists; all other methods/paths fail closed. |
| Header/body parser abuse | 4096-byte header cap; exact string validation; non-empty/non-bytes body rejected without JSON parsing. |
| Stale/malformed/provider-compromised state | Exact immutable M0–M3 classes, bounded fields, injected-clock freshness, generic 503, no partial serialization. |
| Sensitive disclosure | Narrow serializer allowlist; generic errors; tests assert no token/VIN/location/telemetry markers. |
| State/vehicle mutation | No Params/PubMaster/sendcan/control APIs; only provider output is read. |
| File/network side effects | No socket imports/listeners, untrusted file reads, or configuration loading. Future adapters are out of scope. |
| Replay/cache | `no-cache, no-store`; proxy/transport behavior is outside this host-only prototype. |

This does not claim protection for a future server adapter, compromised host, memory disclosure, TLS termination, token provisioning, rate limiting, audit logging, or any vehicle safety/control behavior.

## Reproducible verification

Run from repository root with host Python 3.12:

```bash
python3.12 -m pytest -q openpilot/sunnypilot/starpilot_galaxy/tests
python3.12 -m compileall -q openpilot/sunnypilot/starpilot_galaxy
```

Tests cover default-off provider non-access, invalid settings, missing/wrong authorization, disallowed methods, unknown routes, body/header invalidity, static routes, provider exception, stale/empty/bad snapshots, immutability/non-mutation, allowlisted serialization, secret non-disclosure, and forbidden network/Params/file/control strings. Exact host outputs are in `TEST_OUTPUTS.md`.
