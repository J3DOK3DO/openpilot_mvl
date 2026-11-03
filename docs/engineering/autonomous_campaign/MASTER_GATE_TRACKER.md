# Autonomous campaign gate tracker

Updated 2026-11-03. Decisions describe the stated scope only. **Vehicle release: HOLD.** See [campaign report](../campaign_20261103/CAMPAIGN_MASTER_REPORT.md) for evidence and boundaries.

| Stage | Decision | Accepted evidence or remaining criterion |
| --- | --- | --- |
| M0–M3 bridge prerequisite | PASS (retained host scope) | 51 bridge tests included in consolidated run; default-OFF, read-only bridge. Physical qualification remains open. |
| G03 parameter/message crosswalk | PASS (offline tool); HOLD (semantic migration) | 7 tests; all 254 overlapping parameter keys remain DENY. |
| G05 status view model | PASS (host model); HOLD (native UI) | 13 tests; native MVL renderer and device behavior unverified. |
| G06 Galaxy handler | PASS (host core); HOLD (network/device security) | 22 tests; no live transport or device resource qualification. |
| G08 model catalog | PASS (host catalog); HOLD (runner/AGNOS execution) | 14 tests; no activation, inference, or target execution. |
| G09 control research | PASS (synthetic offline); HOLD (active control) | 261 tests; reason-only output, no CAN or control target. |
| G10 AGNOS inspection | PASS (passive preparation); HOLD (target build/device) | 9 tests; image audit does not establish a booted target. |
| Consolidated offline host regression | PASS | 377 passed, 0 failed, 0 skipped at current HEAD; see TEST_RESULTS.json. |
| Native C3/C4 UI rendering and IPC timing | HOLD | Exact-commit native renderer/device evidence required. |
| Isolated security and hardware bench | HOLD | Auth/transport and hardware evidence required. |
| Full AArch64 AGNOS build and physical boot | HOLD | Cold target build and boot evidence required. |
| Physical Panda safety | HOLD | Firmware/safety identity and bench validation required. |
| Honda OEM collision mitigation and stock ACC | HOLD | FCW/CMBS/AEB and stock ACC behavior across modes/faults required. |
| Exact-commit integrated review and protected rollback | HOLD | Integrated review, rollback exercise, and release decision required. |

No stage is marked FAIL in the current campaign evidence. An unverified stage remains HOLD; a host PASS never promotes a vehicle-facing gate.
