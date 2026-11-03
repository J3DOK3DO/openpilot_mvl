# G06 transport readiness preflight

**Decision: HOLD for live transport and device deployment.** Source-only review at `efdc8b4f0dfcae5c3ddc1ae176bec8a6db5044ea` on `codex/autonomous-campaign`, 2026-11-03. This milestone does not add an adapter or change any vehicle-facing module.

## Verified now

- `GalaxyHandler` is defined only in `openpilot/sunnypilot/starpilot_galaxy/core.py` and exported from that package. A search of non-test `openpilot/` source found no production constructor or registration.
- The core has no socket or HTTP server. It accepts a normalized `GalaxyRequest`, exact GET routes, an explicit default-OFF setting, a token, and an injected snapshot provider. It does not provision a token or secure a transport.
- `python3 -m pytest -p no:cacheprovider -q -ra openpilot/sunnypilot/starpilot_galaxy/tests` passed 22 tests at the exact commit above. Recovery tests passed 2/2 at the same commit.

## Required before a live adapter gate

1. Define a separately reviewed transport boundary: bind address, authenticated access path, TLS termination, proxy behavior, and device network policy.
2. Specify secret generation, storage, rotation, revocation, and failure behavior. Keep secrets out of logs and responses.
3. Enforce raw HTTP normalization before `GalaxyRequest`: duplicate headers, case folding, body framing, request size and timeout limits, and ambiguous `Content-Length`/`Transfer-Encoding` handling.
4. Bound connection concurrency and request rate. Measure CPU, memory, and IPC impact on target hardware.
5. Validate snapshot-provider provenance and staleness on the target; confirm no vehicle control path or state mutation.
6. Run adversarial adapter tests, isolated hardware bench tests, exact-commit review, and protected recovery before any device activation.

The existing [G06 core report](../campaign_20261103/g06/GALAXY_API_CORE.md) and [independent review](../campaign_20261103/g06/INDEPENDENT_CODEX_REVIEW.md) establish only the offline handler boundary. The next eligible work is an offline adapter contract and threat model; implementation should wait for an agreed transport boundary and must remain default OFF.
