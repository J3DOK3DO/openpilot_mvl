# Autonomous campaign gate tracker

Updated 2026-11-04. Decisions describe the stated scope only. **COMMA4_NON_ACTUATING_MVL: PRODUCT_BUILD_INCOMPLETE; comma 4 device tests NOT_TESTED.** See [campaign report](../campaign_20261103/CAMPAIGN_MASTER_REPORT.md) for evidence and boundaries.

| Stage | Decision | Accepted evidence or remaining criterion |
| --- | --- | --- |
| M0–M3 bridge prerequisite | PASS (retained host scope) | 51 bridge tests included in consolidated run; default-OFF, read-only bridge. Physical qualification remains open. |
| G03 parameter/message crosswalk | PASS (pinned source and local host IPC); HOLD (device ABI and semantic migration) | Eight status paths passed pinned schema and local capnp/msgq roundtrip at 6ea2fc997; all 254 overlapping parameter keys remain DENY. |
| G05 status view model and offroad guard | PASS (native host and isolated bench plan); HOLD (C3/C4 device UI) | Actual MVL HomeLayoutSP header path exercised in isolated x86 raylib environment; default OFF and original fallback verified. C3/C4 behavior unverified. |
| G06 Galaxy handler | PASS (host core and metadata); HOLD (network/device security) | Opt-in read-only model metadata from validated injected catalog; 24 core tests; no live transport or device resource qualification. |
| G08 model catalog | PASS (host catalog); HOLD (runner/AGNOS execution) | 15 catalog tests including NUL-path fail-closed regression; two audited ONNX blobs match source LFS hashes; no activation, inference, or target execution. |
| G09 control research | PASS (synthetic offline); HOLD (active control) | 261 tests; reason-only output, no CAN or control target. |
| G10 AGNOS native target probe | PASS (AArch64 library ABI and load); HOLD (full product/device) | AGNOS 19.8.1 comma_arm64 SCons graph PASS; native AArch64 libparams ELF built and dlopen PASS at exact source `162391f`; full product model GPU prerequisite and device boot remain HOLD. |
| Consolidated offline host regression | PASS | 401 passed, 0 failed, 0 skipped at code commit `162391f`; see TEST_RESULTS.json. |
| Native C3/C4 UI rendering and IPC timing | HOLD | Host native renderer PASS; C3/C4 target renderer and device timing required. |
| Isolated security and hardware bench | HOLD | Auth/transport and hardware evidence required. |
| Full AArch64 AGNOS build and physical boot | HOLD | Full cold product build with Qualcomm model compilation and physical boot evidence required. |
| Physical Panda safety | HOLD | Firmware/safety identity and bench validation required. |
| Honda OEM collision mitigation and stock ACC | HOLD | FCW/CMBS/AEB and stock ACC behavior across modes/faults required. |
| Exact-commit integrated review and protected rollback | HOLD | Integrated review, rollback exercise, and release decision required. |

No stage is marked FAIL in the current campaign evidence. An unverified stage remains HOLD; a host PASS never promotes a vehicle-facing gate.

2026-11-04 continuation: G05 isolated bench procedure saved; G06/G08 combined host tests and model pointer/hash verification PASS. Independent exact-commit review at `162391f` PASS for narrow offline scope. All physical, OEM, Panda, recovery and release decisions stay HOLD.

## Restricted comma 4 release profile (2026-11-04)

| Stage | Decision | Basis |
| --- | --- | --- |
| G11 external CAN-FD/HIL | NOT_APPLICABLE_TO_COMMA4_PROFILE | No new active vehicle-control, Panda, ECU or CAN-transmit behavior may enter this candidate; this is not a safety PASS. |
| G12 Honda dynamic OEM validation | NOT_APPLICABLE_TO_COMMA4_PROFILE | No new active behavior in this restricted candidate; comma-only observations do not certify ACC/FCW/CMBS/AEB. |
| Full product artifact and clean-install packaging | BLOCKED | Representative ARM64 library only; stock model contract and complete artifact set unresolved. |
| Comma 4 device qualification | NOT_TESTED | No physical candidate install, startup, thermal, IPC, security or protected rollback result. |

The earlier general vehicle-release HOLD rows in the historical tracker apply to an actuating profile, not as G11/G12 acceptance criteria for this restricted non-actuating profile. See `COMMA4_RELEASE_PROFILE.md`.
