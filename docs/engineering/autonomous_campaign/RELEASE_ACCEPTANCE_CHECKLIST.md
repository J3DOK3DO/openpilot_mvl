# Comma 4 non-actuating release acceptance checklist

Status at the final offline source checkpoint. Historical PASS evidence is scoped to the exact commits in `TEST_RESULTS.json`; any final branch source change requires new exact-commit tests.

| ID | Requirement | Current decision |
| --- | --- | --- |
| S01 | Exact published parent source provenance (`23f516d`) | PASS |
| S02 | Seven pinned submodules | PASS_SOURCE |
| S03 | 283 selected LFS assets hydrated and hashed | PASS_SOURCE |
| S04 | AGNOS 19.8.1 ARM64 SCons graph | PASS_DRY_RUN_ONLY |
| S05 | G03 eight host IPC paths and 254 Params DENY | PASS_HOST |
| S06 | G05 default-OFF native host UI and fallback | PASS_HOST |
| S07 | G06 live registration excluded; local prototype OFF | PASS_HOST_BOUNDARY |
| S08 | G08 read-only catalog and path/hash controls | PASS_HOST |
| S09 | G09 research disconnected from actuation | PASS_SOURCE |
| S10 | Combined host regression at exact `4b25263e8` | PASS_HOST |
| S11 | Source-only QCOM handoff manifest and archive | PASS_SOURCE_ONLY |
| S12 | Six exact-source QCOM outputs | HOLD |
| S13 | Full cold native ARM64 product build | HOLD |
| S14 | Complete source-to-binary package and ABI manifest | HOLD |
| S15 | Independent exact-commit final branch review | PASS_SOURCE_ONLY |
| C4-01–C4-07 | Cold boot, UI, IPC, warning, timing and fallback | NOT_TESTED (7 checks) |
| C4-08 | G06 live service security | NOT_APPLICABLE_TO_COMMA4_PROFILE while unregistered |
| C4-09–C4-11 | Model identity, resource soak, passive Panda/stock identity | NOT_TESTED (3 checks) |
| C4-12 | Physical restoration demonstration | WAIVED_BY_OWNER / NOT_EXECUTED |
| G11/G12 | External HIL and dynamic Honda OEM | NOT_APPLICABLE_TO_COMMA4_PROFILE while no new active control/Panda/ECU/CAN-transmit change |

Checklist denominator is 25 applicable items: S01–S15 plus ten applicable device checks. At this checkpoint, 12/25 = **48%** have accepted scoped PASS evidence; S15 passed independent exact-commit source-only review. Waived and conditional N/A items are excluded. Host PASS does not satisfy physical qualification. Formal release approval is **0% / HOLD** until all applicable criteria and separate installation authorization are met.

AGNOS 19.9 host update (2026-11-06): the official 19.9 image, isolated native graph and selected ABI checks improve G10 prerequisite evidence but do not close the checklist's complete product, binary package or physical items. The formal count remains **12/25 = 48% scoped PASS**, with release approval **0% / HOLD**. C4-12 remains WAIVED_BY_OWNER / NOT_EXECUTED and is excluded from the denominator.

QCOM B1 offline update (2026-11-06): trusted handoff/source bytes, selected LFS and retained 19.9 graph were rechecked; Windows read-only tool/resource facts were incorporated. S12/S13/S14 remain HOLD because all six QCOM captures, a full cold product and complete package/ABI are absent. Applicable device tests remain 0/10. Accepted count remains **12/25 = 48%**, formal release **0% / HOLD**. This update neither executes C4-12 nor changes conditional C4-08/G11/G12 exclusions.

## 2026-11-07 Campaign 1 update

Offline safeguard tooling and build plans add no formal release PASS. S12 six QCOM captures, S13 full ARM64 build, S14 product/ABI package and ten applicable C4 checks remain open. Formal 12/25 = 48%; physical 0/10. C4-08 conditional N/A while G06 unregistered; C4-12 WAIVED_BY_OWNER / NOT_EXECUTED.
