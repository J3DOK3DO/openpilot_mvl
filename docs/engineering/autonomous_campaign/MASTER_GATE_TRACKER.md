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

## Isolated comma 4 release continuation at `feee77a81dbefe4655c5d60c459362005e8e588d`

| Stage | Decision | Exact evidence and remaining criterion |
| --- | --- | --- |
| G03 local IPC and Params | PASS_HOST; HOLD_DEVICE | Eight pinned capnp/msgq paths and crosswalk byte comparison passed. All 254 quarantined Params keys remain DENY. |
| G05 native UI | PASS_HOST; HOLD_DEVICE | Monotonic stale/future supplier snapshot fix integrated. Combined native host suite passed; comma 4 renderer/timing/fallback remains NOT_TESTED. |
| G06 local transport | PASS_HOST_PROTOTYPE; HOLD_DEVICE_SECURITY | Explicit opt-in, owner-private Unix socket, same-UID check and negative request tests passed. Independent review found a socket cleanup race; fixed with inode ownership check and regression. No production registration or target qualification. |
| G08 stock metadata | PASS_HOST; HOLD_TARGET | Read-only catalog and hashes retained. No model selection or inference. |
| G09 offline research | PASS_SYNTHETIC; HOLD_CONTROL | No active actuation admitted to this release profile. |
| G10 complete product | HOLD_PREREQUISITES | Seven submodules absent and 286 LFS pointers unhydrated in isolated checkout; six exact-source QCOM outputs absent. Existing representative ARM64 library evidence is inherited, not a full product. |
| Passive Honda diagnostics | PASS_HOST_TOOL; SUPPLEMENTAL_ONLY | Five bounded collector tests passed. No ACC/OEM safety inference or release gate promotion. |
| Combined software regressions | PASS_HOST | Exact results recorded in TEST_RESULTS.json for this source commit. |
| Comma 4 physical/recovery | NOT_TESTED | Twelve manual checks documented in `COMMA4_DEVICE_TEST_PLAN.md`; no device or installation used. |
| G11/G12 | NOT_APPLICABLE_TO_COMMA4_PROFILE | Conditional on no new control/Panda/ECU/CAN-transmit changes. This is not a safety PASS. |

Release classification remains **PRODUCT_BUILD_INCOMPLETE** and decision **HOLD**.

Independent re-review at `feee77a` found the G06 failed-bind cleanup defect fixed and no additional concrete host-scope security defect. The separate reviewer environment denied Unix socket binding (`EPERM`), so its one passing simulated-race regression supplements the complete 442-test normal-host run; it is not device evidence.

## G10 final product closure attempt — 2026-11-05

| Stage | Decision | Exact evidence / limit |
| --- | --- | --- |
| Seven submodules | PASS_SOURCE | 7/7 exact gitlink checkouts in isolated worktree; no newer substitution. |
| Release-selected LFS | PASS_SOURCE | 283/283 selected assets hydrated and SHA/size verified; three optional large-model pointers intentionally excluded. |
| AGNOS ARM64 SCons graph | PASS_DRY_RUN | Network-disabled AGNOS 19.8.1 builder, exact source `b39410908b15a27ff29f07b451ade468764bb148`, full graph with zero warnings; no binary output. |
| Six MVL QCOM outputs | HOLD_PREREQUISITES | CPU captures rejected by exact-source validator; Dom package incomplete/incompatible; host has no Qualcomm GPU. |
| Full cold product/package | NOT_ATTEMPTED_HOLD | No `SKIP_TINYGRAD_COMPILE`, no substitute outputs, no package or installable binary identity. |
| Combined host software | PASS_HOST | 444 pytest, eight G03 IPC paths, four recovery tests, 254 Params DENY at exact source `b39410908b15a27ff29f07b451ade468764bb148`. |
| Comma 4 physical/recovery | NOT_TESTED | No device modification; twelve checks remain pending. |

Release decision **PRODUCT_BUILD_INCOMPLETE / HOLD**. G11/G12 remain conditionally NOT_APPLICABLE_TO_COMMA4_PROFILE, not safety PASS.

## Final-release scope amendment — 2026-11-05

The owner waiver supersedes historical protected-restoration and rollback rows above for `COMMA4_NON_ACTUATING_MVL`; those rows remain as prior decisions only. C4-12 = **WAIVED_BY_OWNER / NOT_EXECUTED**, automated rollback and stress = **NOT_REQUIRED**, owner-managed previous-version reinstall. G11 external HIL and G12 dynamic Honda OEM remain conditionally **NOT_APPLICABLE_TO_COMMA4_PROFILE** while no active control/Panda/ECU/CAN-transmit change enters source. Full product build, integrity, independent review, C4-01–C4-11 applicable device tests, and separate installation approval remain **HOLD**. Current classification: **PRODUCT_BUILD_INCOMPLETE**.
