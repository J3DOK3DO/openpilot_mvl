# Release readiness

| Classification | Decision | Basis |
| --- | --- | --- |
| SOFTWARE_READY | HOLD | 401 exact-commit host/native tests pass; C3/C4 device UI, G06 live transport and G08 runner qualification remain open. |
| TARGET_BUILD_READY | HOLD | Representative AGNOS 19.8.1 AArch64 native library, ABI and dependencies passed; full cold product build and physical boot remain open. |
| DEVICE_QUALIFIED | HOLD | No exact-device boot, resource, Panda identity, UI, IPC or security evidence. C4-12 restoration demonstration is WAIVED_BY_OWNER / NOT_EXECUTED. |
| VEHICLE_QUALIFIED | HOLD | Honda OEM stock ACC, FCW/CMBS/AEB, override and Panda safety evidence incomplete. |
| DEPLOYMENT_APPROVED | HOLD | All preceding gates and release-owner approval required. |

No installable release is approved. This branch is offline engineering only.

## Offline engineering candidate

`RELEASE_MANIFEST.json` records the pinned baseline, exact verified engineering commit, source/evidence SHA-256s and all open gates. The new continuation source diff fixes G08 NUL-path fail-closed handling and adds its regression; no vehicle-facing or control source changed. A representative ARM64 library was built and hashed, but no installable product package was produced. The branch can be published for engineering review with release HOLD.

Publication status: **published offline engineering candidate** at `40bc2805c00cd44ebcabee6830ecf96c3a1bd33c` on `J3DOK3DO/openpilot_mvl:codex/mvl-starpilot-continuation`. The Windows-authenticated non-force push and remote-ref verification succeeded. Ubuntu HTTPS credentials remain unconfigured. All release classifications remain HOLD.

## 2026-11-04 continuation

Tested source `162391f22567774166a6bd02024a65d969f63b59`: 401 combined host/native tests, eight G03 local IPC paths and four recovery tests PASS. The AGNOS `comma_arm64` SCons graph and native `libparams_c.so` build passed; ELF AArch64 identity, dependencies, RUNPATH, hash and AGNOS `dlopen` are recorded in `G10_BUILD_EVIDENCE_20261104.json`. This is a representative library, not a full cold product. Device, Panda identity observation, target build readiness and deployment approval remain HOLD for this non-actuating profile. G11/G12 external HIL and Honda dynamic OEM testing are conditionally NOT_APPLICABLE_TO_COMMA4_PROFILE; C4-12 is WAIVED_BY_OWNER / NOT_EXECUTED. See `G05_COMMA_BENCH_PLAN.md` for the isolated physical test procedure.

## Final-release owner waiver and build status — 2026-11-05

Full native product build, package integrity, applicable software regression, independent exact-commit review, and actual comma 4 cold boot/UI/IPC/runtime/security checks remain required. The six exact-source QCOM outputs are unavailable, so classification is **PRODUCT_BUILD_INCOMPLETE / HOLD**. This branch is not installable. C4-12 physical restoration demonstration is **WAIVED_BY_OWNER / NOT_EXECUTED**, with no PASS claim. Automated rollback and rollback stress are **NOT_REQUIRED**. Owner-managed factory reset and known-good branch reinstall are outside this campaign and require separate action. The known-good branch identity must be recorded before any separately authorized installation.

Final exact source `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` passed 444 combined host tests, 13 handoff/recovery units, eight G03 IPC paths, seven pinned submodules, 283 selected LFS hashes and source-only handoff verification. Independent source-only review passed. These results do not change **PRODUCT_BUILD_INCOMPLETE / HOLD**: six QCOM outputs, full product package and physical comma 4 evidence remain absent. C4-12 is WAIVED_BY_OWNER / NOT_EXECUTED; C4-08 is N/A while G06 is unregistered.

New reviewed engineering branch [codex/mvl-comma4-final-release-20261105](https://github.com/J3DOK3DO/openpilot_mvl/tree/codex/mvl-comma4-final-release-20261105) published at `627e9171f209d2457706cb694d5169d4de264654` (exact tested source `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`). Publication does not authorize installation; PRODUCT_BUILD_INCOMPLETE / HOLD continues.

## AGNOS 19.9 host readiness update — 2026-11-06

The official 19.9 system image and extracted AArch64 native environment are verified on the Ubuntu host. Frozen 4b product-source SCons graph and toy compiler check passed inside the 19.9 rootfs. A 3,484,104-byte ELF64 AArch64 `libparams_c.so` was built with a terminal SCons completion log; subprocess exit code and 19.9 runtime load were not captured, so this is bounded binary-build evidence only. The version-aware model/product validators preserve the 19.8.1 historical contract and reject 19.9 cross-version substitution. Selected ABI identity is established; GPU/runtime, capacity peak, six QCOM captures, complete product/package and device qualification are still missing. **PRODUCT_BUILD_INCOMPLETE / HOLD** remains. The 25-item release checklist remains 12/25 scoped PASS (48%); formal release 0%/HOLD. This engineering branch is not installable.

## QCOM B1 host checkpoint — 2026-11-06

Fresh host preflight rechecked the external source-only handoff, frozen 4b source, seven pinned gitlinks, 283 selected LFS bytes and two ONNX hashes. The retained AGNOS 19.9 graph contains six QCOM targets and a representative ELF64 AArch64 library, with no runtime load proof. Windows read-only device facts establish model/19.9/tool presence and idle resources; driver/userspace and compilation peaks remain unknown. `HOLD_REQUIRED_CAPACITY_UNKNOWN`; six QCOM captures and full product remain absent. **PRODUCT_BUILD_INCOMPLETE / HOLD**, 12/25 scoped acceptance (48%), formal release 0%/HOLD, applicable device tests 0/10. This branch is not installable. See `QCOM_B1_READINESS_20261106.md`.

## Campaign 1 offline preparation — 2026-11-07

B2 host safeguards and B3/G10 plans are recorded in `COMBINED_CAMPAIGN_FINAL_REPORT_20261107.md`. No device compilation or full product exists. PRODUCT_BUILD_INCOMPLETE / HOLD; software-side 12/25 scoped acceptance (48%), physical 0/10 and final authorization HOLD.

## Campaign 2 read-only update — 2026-11-07

The actual comma mici/AGNOS 19.9 and installed known-good SHA were observed over strict-host-key authenticated read-only SSH. /data lacks observed ext4 project-quota prerequisites; five-second cereal data lacks carState and controlsState; host guardian crash with a descendant is a reproduced limitation. No device write or QCOM compilation occurred. B2 is `B2_HARDWARE_NOT_QUALIFIED`; B3 0/6 and G10 full product/package NOT_BUILT. Representative AArch64 static ABI evidence is not product qualification. `PRODUCT_BUILD_INCOMPLETE / HOLD` persists; scoped acceptance 12/25 = 48%, physical 0/10, final approval 0%/HOLD.
