# Release readiness

| Classification | Decision | Basis |
| --- | --- | --- |
| SOFTWARE_READY | HOLD | Offline prototypes and 389 host tests pass; native UI/service integration and full native regression remain open. |
| TARGET_BUILD_READY | HOLD | No cold AArch64 build or target ABI/dependency qualification. |
| DEVICE_QUALIFIED | HOLD | No exact-device boot, resource, Panda, or protected-recovery evidence. |
| VEHICLE_QUALIFIED | HOLD | Honda OEM stock ACC, FCW/CMBS/AEB, override and Panda safety evidence incomplete. |
| DEPLOYMENT_APPROVED | HOLD | All preceding gates and release-owner approval required. |

No installable release is approved. This branch is offline engineering only.

## Offline engineering candidate

`RELEASE_MANIFEST.json` records the pinned baseline, exact verified engineering commit, source/evidence SHA-256s and all open gates. The source diff adds only a renderer-neutral offroad guard and its tests; no existing vehicle-facing file changed. No binary package or installable artifact was produced. The branch can be published for engineering review with release HOLD.

Publication status: **published offline engineering candidate** at `40bc2805c00cd44ebcabee6830ecf96c3a1bd33c` on `J3DOK3DO/openpilot_mvl:codex/mvl-starpilot-continuation`. The Windows-authenticated non-force push and remote-ref verification succeeded. Ubuntu HTTPS credentials remain unconfigured. All release classifications remain HOLD.
