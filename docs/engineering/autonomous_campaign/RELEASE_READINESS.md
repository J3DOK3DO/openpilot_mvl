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

Publication status: **local branch only**. Non-force push to `origin` failed because the host has no GitHub HTTPS credentials. All release classifications remain HOLD.
