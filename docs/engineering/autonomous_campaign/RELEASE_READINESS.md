# Release readiness

| Classification | Decision | Basis |
| --- | --- | --- |
| SOFTWARE_READY | HOLD | 401 exact-commit host/native tests pass; C3/C4 device UI, G06 live transport and G08 runner qualification remain open. |
| TARGET_BUILD_READY | HOLD | Representative AGNOS 19.8.1 AArch64 native library, ABI and dependencies passed; full cold product build and physical boot remain open. |
| DEVICE_QUALIFIED | HOLD | No exact-device boot, resource, Panda, or protected-recovery evidence. |
| VEHICLE_QUALIFIED | HOLD | Honda OEM stock ACC, FCW/CMBS/AEB, override and Panda safety evidence incomplete. |
| DEPLOYMENT_APPROVED | HOLD | All preceding gates and release-owner approval required. |

No installable release is approved. This branch is offline engineering only.

## Offline engineering candidate

`RELEASE_MANIFEST.json` records the pinned baseline, exact verified engineering commit, source/evidence SHA-256s and all open gates. The new continuation source diff fixes G08 NUL-path fail-closed handling and adds its regression; no vehicle-facing or control source changed. A representative ARM64 library was built and hashed, but no installable product package was produced. The branch can be published for engineering review with release HOLD.

Publication status: **published offline engineering candidate** at `40bc2805c00cd44ebcabee6830ecf96c3a1bd33c` on `J3DOK3DO/openpilot_mvl:codex/mvl-starpilot-continuation`. The Windows-authenticated non-force push and remote-ref verification succeeded. Ubuntu HTTPS credentials remain unconfigured. All release classifications remain HOLD.

## 2026-11-04 continuation

Tested source `162391f22567774166a6bd02024a65d969f63b59`: 401 combined host/native tests, eight G03 local IPC paths and four recovery tests PASS. The AGNOS `comma_arm64` SCons graph and native `libparams_c.so` build passed; ELF AArch64 identity, dependencies, RUNPATH, hash and AGNOS `dlopen` are recorded in `G10_BUILD_EVIDENCE_20261104.json`. This is a representative library, not a full cold product. Device, Panda, Honda OEM, protected rollback, target build readiness and deployment approval remain HOLD. See `G05_COMMA_BENCH_PLAN.md` for the isolated physical test procedure.
