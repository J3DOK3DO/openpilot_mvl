# Native MVL source-backed status contract and M0–M3 boundary

The research input `NativeMvlStatus` is an immutable summary of the existing M0–M3 bridge contract, not a new subscriber. `native_status_from_m0_m3()` accepts only the pinned `BridgeSnapshot` type and maps an accepted projection conservatively. It corresponds exactly to these native MVL projections: `deviceState.started/freeSpacePercent/maxTempC`, `selfdriveState.enabled/active`, and `carState.vEgo/cruiseState.enabled`, whose status freshness and validity originate from `alive`, `valid`, and `logMonoTime` in `openpilot/sunnypilot/starpilot_bridge`.

| Research field | Required source-backed condition | Classifier effect |
|---|---|---|
| `bridge_present` | An M0–M3 immutable snapshot was available | absent → `HOLD/missing_m0_m3_bridge_status` |
| `*_fresh` | Native timestamp accepted by the bridge's monotonic freshness gate | any false → `HOLD/stale_native_mvl_status` |
| `*_valid` | Native `alive`/`valid` and field validation accepted | any false → `HOLD/invalid_native_mvl_status` |
| `selfdrive_active`, `cruise_enabled` | Informational native values only | never grants authority |

Honda identity is deliberately a separate immutable attestation. The prior M0–M3 bridge explicitly excludes CarParams/fingerprint identity; its absence must be denied, never guessed. The exact accepted research context is `HONDA_ACCORD_11G_US`, 2025, hybrid, CAN-FD, Bosch-C. This is a research precondition, not a permission token.

No C6.12 historical evidence is consumed: `historical_c6_12_reused=True` produces `REJECT/NO_C6_12_HISTORICAL_REUSE`.
