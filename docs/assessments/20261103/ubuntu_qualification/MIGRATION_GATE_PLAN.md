# Mandatory MVL-First StarPilot Integration — Detailed Qualification and Execution Plan

**Status:** APPROVED AS AN ENGINEERING PLAN; all vehicle-facing integration, AGNOS release and deployment remain HOLD. **Current evidence baseline:** Ubuntu qualification UQ-20261103.

## A. Governance and baseline invariants

**Single vehicle target:** US 2025 Honda Accord 11th generation Hybrid, Bosch-C harness, CAN-FD, HONDA_ACCORD_11G. Separate other Honda generations and all other brands. No changes to MVL opendbc Honda controller, DBC, radar, Panda safety policy, OEM steering/braking authority, or auto-disengagement logic without a separately authorized, evidence-driven Honda release decision.

**Core rule:** New components are default-OFF, must work with absence of the StarPilot process, must never grant engagement/axis/steering/braking permission, and must not suppress stock urgent warnings. A new branch must be cut from the newly pinned MVL upstream source rather than replacing the existing assessment branch's earlier code. The assessment branch carries documents only.

**Allowed engineering now:** source review, read-only visual and service adapters, unit tests, synthetic simulation, versioned settings translation, pure-math algorithm comparison and native host builds. **Not authorized merely by these findings:** in-car ECU disable sequences, CAN/UDS actuation, firmware flashing, live custom longitudinal steering/braking, or assuming OEM automatic fallback.

### Responsibility matrix

| Role | Accountability |
|---|---|
| Program owner | Approves scope, code promotion, physical tests and release decision; preserves original installations |
| Lead MVL engineer / Codex | Implements isolated typed adapters and reproducible host/native test artifacts |
| Independent code reviewer | Reviews exact pinned diff, schema, dependency, tests, security and fault negatives with a written HOLD/PASS |
| Honda systems owner | Approves CarParams, ECU/radar ownership, stock ACC/AEB/CMBS and control-mode test evidence |
| Panda / safety owner | Verifies native safety policy identity, firmware hash, all permitted messages, denial paths and rollback |
| Device / AGNOS engineer | Qualifies ARM64 binaries, GPU, process scheduling, camera/audio resource budgets and recovery |
| UI / security engineer | Verifies local Galaxy auth, display/warning precedence, privacy and parked-only mutations |
| Release custodian | Protects original MVL branch, records binary and provenance hashes, verifies rollback |

## B. Gate-by-gate execution order

| Gate | Priority | Concrete work and output | Required acceptance | Current result |
|---|---|---|---|---|
| G00 — immutable pins | P0 | Record latest Dom, MVL, opendbc, Panda, NNLC data and change delta; explicit branch ownership and clean tree | Reproducible exact SHAs + hashes, no unintended source changes | PASS |
| G01 — latest native MVL host | P0 | Compile source-local Params, IPC, VisionIPC, longitudinal MPC; run MADS, controls, Honda and Honda safety | Build commands exit 0; native imports; original control behavior unaffected; all attempted test skips disclosed | PASS (selected) |
| G02 — representative StarPilot donor tests | P0 | Compile Dom nanobind IPC, Params; run lane, curve, conditional, SLC, FLM, Galaxy, audio, models etc. | Evidence bound to exact Dom SHA, no vehicle commands, positive and negative results recorded | PASS (306 selected) |
| G03 — ABI and schema crosswalk | P0 | Exhaustive namespace/IPC/Capnp, CarParams, Params, field defaults/type/auth, model data and timing contract comparison | Each transferred field has typed MVL owner, semantic decision, stale/malformed denial and unit test; 254 shared literal keys resolved | NOT DONE |
| G04 — minimal feature registry | P0 | Add MVL-native typed feature registry and read-only adapters, **default OFF**, no hooks to actuation | Adapter OFF parity with pinned MVL; no sendcan/Panda/ECU modification, no critical service dependency | NOT DONE |
| G05 — MVL-native visuals | P1 | Selectively adapt onroad/home/status/path/warning presentation to MVL C3/C4 UI | Native render, screenshot baselines, raylib_nb availability, overlay priority, frame-time and crash recovery | NOT DONE |
| G06 — Galaxy local read-only | P1 | Local authenticated Galaxy server for status/stats/plots/models, no initial mutating endpoints | Auth/CSRF/session expiration, loopback/LAN policy, parked status, no untrusted writes and no driving-process dependency | NOT DONE |
| G07 — optional phone and audio services | P1 | StarPort, companion, BLE bridge, Soloist/Spotify/A2DP, alerts, hotspot as separate processes | Real device bench, GPU/CPU/RAM/thermal budget, urgent warning priority, auth pairing, recovery and no camera starvation | NOT DONE |
| G08 — model/JetLink/laboratory | P1 | Read-only catalog/status only; separate runner artifact ABI and remote USB model pipeline | Digest, compiler/kernels, correct modeld/driver monitoring coexistence, fail-safe fallback, no production paired-lab by assumption | NOT DONE |
| G09 — offline driving policy research | P0 for active features | Compare lane centering, torque/FLM, AOL, SLC, curves, profiles, conditional mode and LongControl **offline only** | Native MVL regression; deterministic adverse scenarios; no direct CAN; stock ACC and MVL safety ownership unchanged | RESEARCH ONLY |
| G10 — physical target ARM64/AGNOS | P0 | Freeze device variant and AGNOS sysroot; cold cross/native build; publish ELF and library closure | Exact device image and firmware hash, no unresolved libs, process health and latency on C4/comma | NOT DONE |
| G11 — Panda firmware safety qualification | P0 | Validate exact Panda F4/H7 policy and independent axis denial, firmware expiry, receive/transmit allowlist | Native safety suite, firmware build hash and real device receipt; deny stale/disallowed control; separate safety owner signoff | NOT DONE |
| G12 — Honda ECU/stock ADAS | P0 | Isolated parked/bench then owner-approved closed-course matrix for fingerprint, radar, ECU ownership, stock ACC, FCW/CMBS/AEB | Recorded safe transitions, restoration, stop/start and override; no unintended messages or loss of factory protection | NOT DONE |
| G13 — final independent review | P0 | Codex and independent reviewer exact-commit critique; close all P0/P1 findings | Written PASS on actual implementation, source/firmware identity and repeated tests; no inferred qualification | NOT DONE |
| G14 — release candidate and rollback | P0 | Build installation artifact only after prior gates, signed/hashed manifest and restoration drill | Verified no-activation default, rollback branch, native binary startup and owner acceptance | HOLD |

## C. First engineering workstream: MVL read-only compatibility boundary

1. **Start from the latest MVL upstream** and create a fresh feature-integration branch. Do not rebase a vehicle controller over Dom or replace MVL opendbc/Panda. Carry only approved feature-domain source.
2. Add a typed MVL-side adapter package with *no* sendcan, UDS, Panda or vehicle actuation imports. It may subscribe to existing MVL messages and produce copies of read-only status structures, not change their authors or timestamps.
3. Implement explicit versioned messages and a feature registry defaulting every new feature OFF. An absent, corrupted or stale setting must not enable anything. Comma processes cannot depend on Galaxy or StarPort for engagement.
4. Build a settings crosswalk from both schemas; the previously identified 254 identical literal key names require owner/type/default/lifetime review. Do not bulk-migrate Params, calibration, model artifacts or replay caches.
5. Add test fixtures for missing CarParams, wrong fingerprint, stale clock, invalid sensor data, conflicting UI states, process restart, bad auth and storage error.
6. Prove binary and message independence: MVL stock startup and stock ACC/lat authority must be behaviorally identical when all new features are OFF. Require exact source snapshots and logged negative tests.
7. Do not promote any driving configuration from this workstream; produce one reviewed documentation-and-test PR per feature family.

**Acceptance:** zero vehicle-facing files changed at baseline, no new transmit dependencies, tests prove default-off parity, all integration patches contain a feature owner and rollback.

## D. Non-driving feature workstreams

### D1. UI visual adaptation (default first)

Separate compact and large layouts; preserve MVL camera geometry, CAN-FD lane-path/object drawing, driver-monitoring and emergency alerts. Reimplement only style/render adapters rather than importing Dom's UI lifecycle. Required tests: raylib_nb native dependency, C3/C4 scaling and touch, HUD icon/source ownership, warning-overlay layering, side-camera PiP, night themes, bounded graphics allocations, frame pacing and crash/restart. Source test families cover native UI, visual spot monitor, sound-pack status and map/navigation presentation.

**Acceptance:** read-only display-only outputs, emergency warnings visually dominant, no UI blocking controlsd/modeld, deterministic fallback to standard MVL on component failure.

### D2. Galaxy local read-only

Start status-only behind authentication; do not initially expose update/install/branch-switch, car selection, privacy data export, settings mutation or replay command execution. Review all HTTP APIs, BLE bridge, CSRF, session expiry, cookie scope, LAN versus local bind, file paths, uploaded media and snapshots. A user interface showing a value does not grant authority to change that setting. Keep service optional and offroad-aware.

**Acceptance:** invalid or anonymous requests fail closed; no onroad state change; safe error behavior when service disconnected.

### D3. StarPort, companion apps, audio and model tools

Separate StarPort projection from Galaxy web/app pairing. Bench C4 GPU/encoder and USB/Bluetooth ownership, plus modeld driver-monitoring memory/latency contention. Ensure urgent soundd alerts preempt media; hardware display and audio ownership must restore after disconnect/crash. Model Manager can show catalog/digest/read-only status but may not replace MVL modeld or kernel artifacts without AGNOS runtime verification. JetLink and paired model lab remain experimental until exact compiler and model provenance is closed.

**Acceptance:** on-device native build and resource-trace PASS, no safety-critical process starvation or unauthorized external connectivity, recovery under unplug/restart/thermal pressure.

### D4. Sentry, analytics, maps, privacy and software updates

Parked-only opt-in camera motion, storage-retention limits, battery/power protection and consent for push; no user telemetry egress by default. Keep MVL mapd/navd owner and avoid routing SLC targets through unverified map data. Preserve MVL OTA and rollback; new pages may display status but cannot change release branch or silently install packages.

**Acceptance:** written threat model, privacy consent, offroad/parked gates, network-drop recovery and no change to car control chain.

## E. Driving-feature research — explicitly offline-only

| Research feature | Native MVL comparison | Required simulation before any Honda proposal |
|---|---|---|
| StarPilot independent AOL | MVL MADS axis states, Panda permission, Honda stock ACC authority | Paused versus active, steering request denial, brake/ACC withdrawal, malformed CP, stale CAN and restart |
| Lane centering and lane offset | MVL selected lateral controller, NNLC and torque extension | Single-line/road-edge confidence, driver torque override, actuator clipping, lane uncertainty, control mode changes |
| FLM/torque learning | MVL torque limits, Honda EPS and steering delay | Bound every learned parameter; no runtime auto-learning until device measurement and steering safety proof |
| SLC speed-limit adoption | MVL smart cruise and Honda Card stock cruise/SET/RES | Bad map/vision limits, source arbitration, rounding/offset bounds and zero unintended cruise changes |
| Curve speed | MVL mapd and long planner | Wrong curvature, grade/lead/stop, stale model, driver chosen speed, no planner control while OFF |
| Conditional Experimental/Chill | MVL planner axis/engagement state | Clock/replay provenance, stop priority, road/lead triggers and denial under OEM stock long |
| Longitudinal profiles and planner | MVL Bosch-C long, radar/ECU, OEM ADAS | Stop/start, lead loss, fault transitions, source freshness, no unwanted AEB/FCW/CMBS disable |
| Wheel actions and other driving settings | MVL native Honda buttons and cruise logic | Current button source, duplicate actions, driver override, OEM ownership, no device startup dependency |

**No simulated success can substitute for Panda/vehicle safety and actual OEM AEB/CMBS evidence.** Use only native MVL tests and newly generated deterministic fixtures for each proposed adapter; never count older C6-12 or C7 route tests as fresh Dom-to-MVL qualification.

## F. Minimum negative/failure matrix for every future adapter

Every new integration must cover: no or invalid CarParams; non-Accord brand/fingerprint; mismatched Bosch-C harness or Panda safety word; stale/overflowed/malformed CAN and Capnp; clock jump; service crash/restart; disconnected Galaxy/StarPort; modeld and driver-monitoring overload; wrong cached settings schema; normal and emergency disengagement; brake and accelerator override; EPS temporary/permanent faults; low speed and standstill; turn-signal/lane-change interaction; saved setting corruption; storage full; power and thermal faults; reboot and rollback.

Driving-specific proposals require additionally validated OEM stock ACC, FCW/CMBS/AEB and collision-warning state in all actual supported modes, with physical owner signoff. All optional features OFF must be indistinguishable from original MVL behavior.

## G. Reproducible Ubuntu host commands (not installation instructions)

These are **offline source-host testing examples**, to be run only in separately pinned development worktrees.

    # Identify source and submodules (no vehicle)
    git rev-parse HEAD
    git submodule status
    git status --porcelain

    # Reuse the pinned tools or build a new isolated venv with Python 3.12.
    # Export PYTHONPATH for the exact worktree and its msgq/opendbc submodules.
    scons --minimal -j3 openpilot/common/libparams_c.so
    scons --minimal -j3 msgq_repo/msgq/ipc_pyx.so

    # Selected MVL regression families
    python -m pytest -q -ra openpilot/sunnypilot/mads/tests openpilot/selfdrive/controls/tests
    python -m pytest -q -ra opendbc_repo/opendbc/car/honda/tests opendbc_repo/opendbc/safety/tests/test_honda.py

    # Artifact and dependency identity
    sha256sum openpilot/common/libparams_c.so
    file openpilot/common/libparams_c.so
    ldd openpilot/common/libparams_c.so

Dom's native IPC command uses its own source-defined nanobind module **msgq/_ipc.so**, not MVL's ipc_pyx.so. Never mix binary packages between the source revisions in test results or release artifacts. Host tests are x86_64, not a comma ARM64 build.

## H. Evidence package rules

Each feature PR or future release must include a complete ledger row: exact source blob/SHA; car capability/CP gate; source owner and settings types; imported dependencies and licensing; disabled-state output; runtime service and deadline; unit tests with skipped counts; negative/fault results; native build log; security and privacy review; device/AGNOS performance; owner/safety signoff; rollback procedure and release decision.

**FAIL/HOLD is a valid completed engineering disposition.** Do not suppress skipped tests, substitute an unrelated vehicle's safety evidence, silently change OEM behavior, or infer that vehicle sensors/FCW/AEB remain available from one successful ACC test.

## I. Immediate next promotion decision

**GO (engineering only):** A single read-only MVL UI/telemetry adapter with all flags OFF, native unit tests and an exact-commit independent review.

**CONDITIONAL:** Galaxy local read-only, audio/visual overlays and StarPort/companion workbench after authorizing network, privacy and hardware boundaries.

**HOLD:** Dom Honda adapter, Panda safety changes, active AOL/lane-control injection, speed-limit auto adoption, custom Bosch-C longitudinal and release-candidate installation.

**Full native/vehicle qualification is not yet closed**: exact AGNOS build, actual comma/Panda firmware and OEM Honda collision-mitigation safety evidence remain mandatory, and no device-level PASS can be inferred from the present host logs.
