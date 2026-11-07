# Blockers and dependencies

Updated 2026-11-04. These are **HOLD** gates, not observed failures of the current host suite.

| Blocker | Remediation attempted or evidence gathered | Dependency to clear |
| --- | --- | --- |
| Parameter migration provenance and semantics | G03 marked caller metadata unattested; 254/254 overlapping keys remain DENY. | Source-attested mapping and separate semantic review. |
| Native UI and IPC behavior | G05 host view model passed; high/critical OEM/MVL alerts suppress optional panels. | Native C3/C4 render and device timing tests. |
| Galaxy live security | G06 authenticated GET-only handler passed host tests; default OFF. | Isolated network/auth transport and device resource security review. |
| Model execution | G08 catalog/hash checks passed host tests; no runner enabled. | Model runner, target compatibility, and AGNOS execution qualification. |
| Vehicle control safety | G09 synthetic reason-only evaluator passed; no CAN/control values emitted. | Physical Panda and Honda OEM stock ACC/FCW/CMBS/AEB validation across faults and modes. |
| Target build and boot | G10 inspected AGNOS 19.8.1 image; host native libraries are x86-64; standard AArch64 compiler tools were absent in the recorded environment. | Toolchain and capacity, full AArch64 cold build, physical device boot. |
| Release and recovery | Consolidated host regression passed; no installable combined branch was authorized. | Exact-commit integrated review and protected rollback exercise. |

Earlier review defects were corrected and retested, as recorded in the [master report](../campaign_20261103/CAMPAIGN_MASTER_REPORT.md). The host suite currently has no failing tests.

G06 preflight at `efdc8b4f0dfcae5c3ddc1ae176bec8a6db5044ea` confirmed no production adapter or registration. See [transport readiness](G06_TRANSPORT_READINESS.md); live transport remains HOLD.

Background host check: standard `aarch64-linux-gnu-gcc` absent from PATH; no cold ARM64 build attempted. Exact AGNOS image hash matched prior evidence. See `BUILD_EVIDENCE.json`.

Native raylib UI startup test at `e65dc8aa9053e53d41fb9a7c2f721b3e819557c6` was BLOCKED during collection by missing `capnp` in system Python. A read-only cached pycapnp retry then hit missing `opendbc`; no UI process started. Do not count the 389 offline host tests as native UI startup evidence.

G03 exact-source field names, ordinals and types now have machine-readable PASS at `accfcb90a4794df2ab162ff35267fff3c0d3b0e7`; IPC binding ABI, runtime update/timing and semantic Params migration remain HOLD. The 254-key quarantine is unchanged.

**Publication resolved:** `codex/mvl-starpilot-continuation` was published to `J3DOK3DO/openpilot_mvl` at `40bc2805c00cd44ebcabee6830ecf96c3a1bd33c` via the already authenticated Windows Git helper. The remote branch SHA was independently checked after a non-force push. The earlier local Ubuntu HTTPS push failure remains historically valid but is no longer a publication blocker. Ubuntu's own HTTPS Git credentials are still unconfigured; use the authenticated helper or configure authorized SSH/credential management for later pushes. **All physical and release-qualification HOLDs remain.**

## Manual continuation at 6ea2fc997

N1 isolated x86 native renderer and G03 local capnp/msgq roundtrip PASS; 34 focused tests and 400 combined exact-commit tests passed. This clears the host dependency-collection obstacle only. Device ABI, C3/C4 rendering and timing remain HOLD. All 254 Params keys remain DENY.

N2 G10 preflight: AGNOS 19.8.1 reference hash matched; extracted libc is AArch64 and Clang emitted a toy AArch64 object. Free root disk was 13,554,855,936 bytes, below the campaign 15 GiB build threshold; AArch64 sysroot, usable SCons environment and container execution unavailable. Product build was not attempted. See `N2_ARM64_PREFLIGHT_20261103.json`.

N4 opt-in read-only Galaxy model metadata passed independent review after direct-catalog validation and bounded-serialization fixes. Live Galaxy transport and model execution remain HOLD.

Previous scheduled invocation failure: available Codex app-server and SQLite logs did not expose a scheduler execution record or attributable failure cause. Treat cause as unresolved; manual campaign continued. Ubuntu HTTPS DNS/credentials remain unavailable in this sandbox; publication requires authorized helper or connected GitHub path.

## 2026-11-04 G10 continuation

Disk capacity rose above the 15 GiB preflight threshold (root 18,244,243,456 bytes; separate build volume 41,109,618,688 bytes before extraction). No pinned source, historical evidence, AGNOS reference or backup was deleted. The AGNOS 19.8.1 rootfs copy and its own AArch64 Python/Clang/capnpc dependencies ran under network-disabled emulation; the full SCons graph dry-run passed. Initial native library build failed only because `capnpc` was omitted from PATH, then passed using the image venv. A representative `libparams_c.so` is ARM64, resolves on AGNOS and loads; see `G10_BUILD_EVIDENCE_20261104.json`. Full cold product build remains HOLD because modeld selects Qualcomm GPU model/warp compilation and this isolated builder has no target GPU/runtime. Clean PR checkout ONNX blobs are LFS pointers; audited blobs match both pointer hashes but are external to the checkout.

A copied build submodule made the first 162391f host regression report 400 PASS/1 FAIL because the host crosswalk test expects no local car schema. A clean exact-commit host checkout resolved this setup mismatch: 401 PASS, 0 FAIL, 8 G03 IPC paths, 4 recovery tests. The G08 NUL-path exception was reproduced, fixed and covered by a regression. G05 physical bench plan is ready but C3/C4 UI, G06 live security, G08 runner, protected rollback, Panda, Honda OEM and deployment approval have no physical evidence.

## Restricted comma 4 profile interpretation (2026-11-04)

For `COMMA4_NON_ACTUATING_MVL`, external CAN-FD/HIL hardware and Honda dynamic OEM maneuvers are not acceptance blockers, provided the release contains no new active control, Panda, ECU or CAN/UDS transmit behavior. They are NOT_APPLICABLE_TO_COMMA4_PROFILE, not PASS. The real blockers are full product/model artifact provenance, safe packaging, G05/G06 device integration and physical comma 4 evidence including protected recovery. The older Panda/Honda rows remain historical requirements for any future actuating vehicle profile.

## Isolated comma 4 continuation at `feee77a81dbefe4655c5d60c459362005e8e588d`

| HOLD | Remediation and exact remaining dependency |
| --- | --- |
| Complete product package | Read-only preflight found 7 missing submodule checkouts and 286 unhydrated LFS assets; no oversized committed blobs or restricted source changes. Hydrate pinned source assets in an isolated build checkout and provide six source-matched QCOM model/warp artifacts. No cold full build was attempted because these prerequisites failed. |
| MVL QCOM model provenance | Both ONNX audit blobs match LFS hashes. Preserved six tinygrad captures are CPU/LLVM; Dom's QCOM package lacks MVL `driving_tinygrad.pkl` and binds a different compiler source inventory. Static exact-source manifest validator added; obtain genuine MVL QCOM outputs and target execution evidence. |
| G05 on-device native UI | Monotonic stale snapshot bug fixed and host tests passed. Execute the twelve-check comma 4 plan for actual rendering, timing, warning priority, fault fallback and protected restore. |
| G06 device security | Opt-in same-UID Unix prototype passed negative host tests. Independent review's failed-bind cleanup race was fixed and regression tested. Production registration is absent. Bound callback behavior and qualify target access, resource use, shutdown and network isolation before device enablement. |
| Physical release | No comma 4 device session, full package, restoration exercise or installation authorization. Classification remains PRODUCT_BUILD_INCOMPLETE; comma 4 device NOT_TESTED. |

G11 external HIL and G12 Honda dynamic OEM are conditionally NOT_APPLICABLE_TO_COMMA4_PROFILE for this non-actuating diff. Passive Honda observations cannot establish Panda or OEM safety.

## G10 closure attempt 2026-11-05

Seven pinned submodules and all 283 release-selected LFS objects are now restored and verified in the new isolated build worktree; they are no longer blockers there. The single primary product dependency is six MVL-exact QCOM model/warp outputs. The host has no `/dev/kgsl-3d0`; preserved CPU captures fail the QCOM validator, and Dom artifacts are source-incompatible and incomplete. No full cold build was attempted. A separately authorized, isolated comma 4 build route or other matching Qualcomm build host is required. The known-good installation, AGNOS reference, previous branches and PR #1 remain unchanged. Device checks and protected restoration remain NOT_TESTED.

Independent review at `b39410908b15a27ff29f07b451ade468764bb148` accepted the submodule LFS preflight correction and the G05/G06 device-harness limitations. Source preflight and ARM64 graph pass at this exact commit, but all six exact-source QCOM outputs remain unavailable; PRODUCT_BUILD_INCOMPLETE and device NOT_TESTED are unchanged.

## 2026-11-05 final-release scope reconciliation

The owner waived C4-12 physical restoration demonstration: **WAIVED_BY_OWNER / NOT_EXECUTED**, never PASS. Automated rollback and rollback stress are NOT_REQUIRED. Historical protected-restoration statements above are superseded for this restricted profile. The owner retains responsibility for factory reset and reinstall of the recorded known-good branch; no reset or restore was executed. Six exact-source QCOM outputs, a full cold product package, applicable comma 4 device tests and separate installation authorization remain blocking. G06 production transport remains OFF/unregistered until target security qualification.

Final source `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` is clean and exact preflight PASS with seven pinned submodules and 283 selected LFS inputs. A verified source-only handoff at `/mnt/commadrive/MVL_QCOM_HANDOFF_4b25263_20261105` carries no valid stock QCOM outputs. No `/dev/kgsl-3d0` exists on Ubuntu; six QCOM outputs and full cold native product remain genuinely external/authorization gated. Physical C4 checks and installed known-good branch identity remain unresolved. The owner waiver does not promote product or device gates.

## QCOM continuation, 2026-11-06

The verified source-only handoff is intact. Read-only SSH to the configured `comma` alias failed `NO_ROUTE_TO_HOST`; no device architecture, AGNOS, GPU, available resources, compiler environment, installed known-good branch or SHA was observed. There was no device copy, compilation, installation or modification. The isolated Ubuntu host has no Qualcomm GPU and has no valid six-output QCOM package. Thus QCOM compilation, full cold ARM64 product build, binary ABI manifest and package remain `NOT_ATTEMPTED / HOLD`. Separate device-side compilation authorization and a reachable compatible runtime are external dependencies. The focused offline observer/inspector tests passed 12/12 at `c5c2cb367a451dd8f6476e3bd365649938ba16e4`. C4-08 stays excluded while G06 is unregistered; C4-12 remains owner-waived and unexecuted.

## AGNOS 19.9 / QCOM readiness update — 2026-11-06

Fresh user-supplied read-only Windows SSH observations supersede the earlier Ubuntu *device-unknown* inference: actual device is comma mici, AArch64, AGNOS 19.9, with `/dev/kgsl-3d0` and the recorded known-good branch/SHA. Ubuntu SSH remains unusable and was not retried. The 19.8.1 artifact recorder and native inspector target the wrong AGNOS version for this device (`BUILD_TARGET_MISMATCH`); no verified ABI break is known. An exact 19.9 image/rootfs and package inventory, measured isolated build storage/thermal working set, and six source-matched QCOM captures remain HOLD. `AGNOS199_QCOM_READINESS_20261106.md` records the capacity arithmetic and next dependency checks. No device writes or product build occurred; `PRODUCT_BUILD_INCOMPLETE / HOLD`, applicable C4 `NOT_TESTED`, C4-08 N/A while G06 is OFF, and C4-12 `WAIVED_BY_OWNER / NOT_EXECUTED` remain unchanged.

## AGNOS 19.9 host campaign — 2026-11-06

The former unknown 19.9 image/toolchain prerequisite is resolved for **host-only** work: official manifest and both sparse/raw hashes verified; isolated AArch64 19.9 rootfs executes SCons/capnpc/Clang, and the full graph dry run passed. A representative ELF64 AArch64 `libparams_c.so` was built at frozen 4b source (SHA-256 `2594c615...`; completion in SCons log), with no captured process exit code or 19.9 runtime load. Selected ABI files are byte-identical to retained 19.8.1 reference, but this does not establish whole-device or GPU compatibility. The exact 19.9 image and native environment evidence is in `AGNOS199_IMAGE_PROVENANCE.json`, `AGNOS199_DEPENDENCY_INVENTORY.json` and `AGNOS199_BUILD_TEST_RESULTS.json`.

Remaining external gates: six exact-source QCOM outputs require a separately authorized compatible Qualcomm runtime and source transfer/compilation; actual GPU compiler scratch, thermal/RAM peak and complete staging capacity remain unmeasured; full cold product/package, device C4 tests and separate installation approval remain absent. The 19.9 artifact contract rejects cross-version substitutions. No installed known-good tree/cache, Panda, ECU, Honda safety policy or vehicle control source was changed. `PRODUCT_BUILD_INCOMPLETE / HOLD` persists. C4-12 is owner-waived/unexecuted; G11/G12 are only conditionally N/A for this non-actuating profile.

## QCOM B1 2026-11-06 blocker reconciliation

AGNOS 19.9 host image/rootfs, SCons/capnpc/Python tool presence, exact handoff and frozen source are host prerequisites now observed or verified; earlier unknown wording above is historical. The current device route still lacks Qualcomm driver/userspace identity and measured six-target GPU scratch, output/TMPDIR/cache high-water, peak RSS and sustained thermal evidence. `/data` snapshot 9,284,868 KiB cannot close capacity with unknown peaks; `HOLD_REQUIRED_CAPACITY_UNKNOWN`. Six exact-source captures, full cold product, complete package/ABI, 0/10 applicable device tests and separate device-side compilation/installation approvals remain open. No device files or known-good installation were changed. G06 OFF; 254 Params DENY; C4-08 conditional N/A, C4-12 waived/unexecuted, G11/G12 conditional N/A only for unchanged non-actuating behavior.

## Campaign 1 continuation — 2026-11-07

Device aggregate quota, runtime filesystem support and full build scratch peak remain unverified. The 512 MiB candidate is below measured source checkout size. Live `carState`/`controlsState` and a tested independent abort controller are absent; actual GPU containment is unknown. Six QCOM outputs, complete ARM64 product, target ABI/runtime and physical C4 tests remain absent. Offline preparation proceeds; device execution stays NO_GO.

## Campaign 2 actual-hardware blockers — 2026-11-07

Read-only AGNOS 19.9 device inspection found /data ext4 without the observed `project`/`quota` features or project-quota mount option. There is no tested alternate hard aggregate limit that covers source, Git metadata, cache, TMPDIR, HOME, outputs and logs. No mount or filesystem was changed. A separately authorized, isolated enforcement proof or a qualified external Qualcomm runtime is required; capacity remains unknown despite 9,284,160 KiB idle free space.

A five-second passive subscription yielded 51 pandaStates but zero carState/controlsState messages. It cannot establish continuously parked/stationary/disengaged conditions. GPU allocation containment, sustained thermal behavior, device OOM, run ownership and cleanup remain untested. The host guardian fix stops same-group children on normal exit and abort, but independent review reproduced a child surviving guardian SIGKILL; device watchdog qualification is HOLD. No source staging, compilation, installation, Panda/ECU/CAN or vehicle control action is authorized.

Six exact-source QCOM outputs remain 0/6, full ARM64 product and complete package do not exist, physical C4 checks remain 0/10 and separate installation approval remains outstanding. The next permitted work is offline alternative-quota/watchdog research and an independent non-production proof; actual device write requires separate owner authorization after all safeguards pass.
