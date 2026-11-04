# G05 isolated comma native UI bench plan

Status: **PROCEDURE READY; DEVICE EVIDENCE HOLD.** This is a test plan for a separately authorized, isolated C3/C4 bench. It does not authorize installation on a vehicle or a connected comma device.

## Entry conditions

- Record device model, serial, AGNOS version, active source commit, package hash, Panda firmware/safety identity, operator, UTC time, and recovery image hash. Use a bench device disconnected from vehicle CAN, actuators, and the road.
- Preserve and verify a restorable known-good image and a protected recovery path before any candidate is booted. Have an independent observer and a stop/rollback operator.
- Confirm candidate provenance, target ABI and dynamic dependencies. A partial ARM64 binary build or host UI PASS does not meet this entry condition for a candidate boot.
- Keep StarPilot off by default. Do not enable longitudinal, lateral, model execution, Galaxy transport, or experimental control.

## Capture and acceptance matrix

| Case | Stimulus and observation | Acceptance evidence |
| --- | --- | --- |
| Baseline | Boot known-good image, record native UI process, frame cadence, CPU/RAM and offroad alert behavior. | Time-stamped baseline logs and screen capture; recovery boot verified. |
| Startup and default OFF | On an approved bench candidate, cold boot with no StarPilot setting, then with explicit OFF. Observe native HomeLayoutSP import, initialization, and original HomeLayout fallback. | No crash or blank display; optional panel absent; original UI usable throughout. |
| Read-only status timing | Feed a deterministic local replay of valid, stale, missing, malformed and out-of-order status messages without vehicle CAN. Record source timestamp, IPC arrival and rendered frame timestamp. | Values never exceed their defined freshness window; stale/missing data is suppressed or clearly unknown; no UI thread stall. Record p50, p95, p99 and maximum latency for each device model. |
| Warning priority | Replay Honda OEM and MVL high/critical alerts alongside optional status. Include simultaneous and rapidly changing alerts. | OEM/MVL alerts remain visible at native priority; optional panels never obscure, delay or replace them. Capture frame sequence and event timestamps. |
| Fault fallback | Kill the read-only status publisher, deny its IPC endpoint, corrupt one message, and restart it. Separately exercise renderer import/initialization failure. | Original UI continues or recovers; no repeated crash loop, frozen warning, stale false-safe status or control side effect. |
| Resource budget | Repeat startup and replay for a sustained bench interval with rendering traces, CPU/RAM, IPC queue depth and dropped-frame counts. | Compare against measured known-good baseline and a separately approved device-specific budget; no unexplained growth. |
| Protected recovery | With the independent observer, trigger the documented rollback from each fault condition on the isolated bench. | Restored known-good image hash, clean boot, original UI, and preserved logs; no vehicle connection. |

## Stop conditions and record

Stop immediately on warning suppression, blank/frozen UI, unbounded latency, device instability, unexpected network listener, control-path effect, or failed rollback. Preserve logs and mark G05 DEVICE HOLD/FAIL until root cause and a fresh exact-commit run are reviewed. Do not promote DEVICE_QUALIFIED from a host test, QEMU build, or a single device model. Record every case with exact candidate SHA, device identity, stimulus trace hash, raw timestamps, screen capture hash, operator and independent reviewer decision.

G05 bench completion remains dependent on target build qualification, device access and explicit release-owner authorization. Honda OEM/Panda/vehicle qualification and deployment approval remain separate HOLD gates.
