# MVL-first StarPilot read-only bridge architecture (M0–M3)

**Target:** 2025 US Honda Accord 11G Hybrid, Bosch-C/CAN-FD. **Baseline:** mvl-boston/openpilot `sp-honda-dev-202608` @ `376c44b5731b2655e5c2f301b73c9729eb499e91`; opendbc `3fec9a418a659de31d7b1f494193161697a35071`.

## Boundary and operating model

The new `openpilot/sunnypilot/starpilot_bridge/` package is a dormant, import-safe, pure-Python status projection library. It does not register a manager process, execute at boot, run a server, write Params, publish messages, create CAN/UDS commands, import Panda or Honda control internals, or modify any pre-existing MVL runtime source. Source files are separate from the Dom tree; no Dom binary or generated Cereal/Nanobind modules are imported.

```
MVL-owned existing services (read-only)
  deviceState / selfdriveState / carState
                 |
       [caller-owned SubMaster]
                 |
       [optional explicit factory]
                 |
    FeatureRegistry (all OFF unless strict bool opt-in)
                 |
   ReadOnlyStatusAdapter (alive/valid/time/range gates)
                 |
         immutable BridgeSnapshot
                 |
       future MVL-native visual UI
               (NOT WIRED)
```

The package exposes only read-side data. There is **no** corresponding publish/command channel. Failure of its caller cannot block MVL control services because no production process dependency is registered. The optional `create_mvl_submaster(registry)` function imports `openpilot.cereal.messaging` lazily, creates a **SubMaster** only for explicitly selected status topics, and refuses all-OFF invocation before any native import.

## Security and safety invariants

1. Only the exact native FeatureRegistry type is accepted by the adapter and subscriber factory; subclasses cannot override topic allowlists.

Every feature (`device_status`, `selfdrive_status`, `car_status`) defaults OFF. Unknown feature names and non-exact-booleans are rejected. Runtime settings are in-memory only; **zero** existing saved Params keys are migrated or altered.
2. With all options OFF, adapter access to the supplied source and injected clock is short-circuited and no subscriber can be started via the factory. The empty snapshot uses now_ns=0. There are no production startup hooks.
3. Only `deviceState`, `selfdriveState` and `carState` are allowlisted. Native MVL remains owner, producer and timing authority for these messages.
4. Each enabled read requires true `alive`, true `valid`, positive monotonic topic timestamp, no future timestamp, age at most 2 seconds by default, strictly increasing per-topic timestamps across accepted reads and no clock rollback. A failed gate yields no status value and a reason, never stale data.
5. Payload projection is field-only, immutable, bounded and no raw native object escapes. No VIN, fingerprint, safety flags, steering/braking/ACC command, calibration, location, secret or model tensor is returned.
6. A selfdrive `active` boolean or car `cruise_enabled` is **informational only**, never an engagement grant or OEM safety guarantee.
7. The package contains no sockets, HTTP routes, telemetry export, persisted files or writes. Any future Galaxy service needs separate authentication, consent, local-only boundary and security review.
8. Every future UI feature must be separately default-OFF, keep controlsd/soundd/driver-monitoring independent, and preserve urgent onroad warning priority.

## Out-of-scope, explicit HOLD

No importing Dom AOL, lane centering actuator control, FLM/learned torque, SLC cruise writes, curve or longitudinal planner authority, Galaxy mutation API, StarPort audio/video, modeld runners, vehicle ECU diagnostics, Panda firmware/safety, Bosch-C long, carcontroller or any Honda can/uds owner. The native host regression is not an AGNOS ARM64, device, Panda hardware, FCW/AEB/CMBS or road release qualification.

## Next engineering gate (not part of M0–M3)

A dedicated M4 UI prototype can consume the immutable snapshot only *after* independent reviewed code and native host tests are accepted. This branch must not be treated as an installable vehicle release. Device and safety work follow the existing M5–M14 qualification plan with distinct evidence gates.
