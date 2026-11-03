# Accord 11G StarPilot:Dom → MVL — Final Incremental Ubuntu Qualification, 3 November 2026

**Campaign:** UQ-20261103, continuation on the protected MVL-first architecture. **Target:** 2025 US Honda Accord 11G Hybrid, Bosch-C/CAN-FD. **Classification:** Offline assessment evidence PASS for individually identified tests; full integrated vehicle qualification **HOLD**.

This supplement does **not** restart the complete 9,269-file Dom inventory, the updated November 3 9,305-file source audit, or the 32-feature-family disposition. It adds current native results, donor FLM changes, independent review, AGNOS evidence, and residual release gates. No Honda CarController, Panda safety logic, ECU firmware, device software or car was modified.

## 1. Exact pinned inputs

| Subject | Commit / identity |
|---|---|
| mvl-boston/openpilot:sp-honda-dev-202608 | 376c44b5731b2655e5c2f301b73c9729eb499e91 |
| MVL opendbc | 3fec9a418a659de31d7b1f494193161697a35071 |
| MVL Panda | 8a16e089b88593914823743df29e1c30b7dd3e00 |
| Donor version used in prior Ubuntu qualification | 10d170e799aa8d492a3f604ef8e91aafa3c11408 |
| Latest donor assessed in this increment | be17536f2b48fca023cc48b0e73d52a40683456b |
| Ubuntu MVL documentation assessment branch starting point | cb1c451c4e470e20ed4e6b66bb13617ba9de673a |
| Offline AGNOS image | Version 19.8.1; SHA-256 98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8 |

The donor advanced by two commits and **five changed files** beyond the previous native-qualification pin: FLM global runtime, FLM live-tracking ingress, two corresponding FLM test modules and prebuilt.json. This precise delta is recorded in [latest_flm_delta_to_be175.csv](latest_flm_delta_to_be175.csv). None of the five files is a Honda controller or Panda safety change. The FLM changes concern causal tuning evidence and valid timestamp intervals; they do not establish live Honda steering authority.

## 2. Evidence-based native test ledger

| ID | Test or build scope | Observed result | Qualification limit |
|---|---|---|---|
| R-01 | Prior latest MVL host-native and Honda/Panda simulator baseline | 1,140 passed, 613 skipped, no failures | Prior Ubuntu evidence; does not verify physical Panda |
| R-02 | Fresh MVL MADS states/steering, torque buffer and Honda safety hooks | **1,080 passed; 612 skipped; 1,190 subtests passed; exit 0** | Same subject area as R-01; not 1,080 new unique tests |
| R-03 | Prior selected donor driving test modules | 149 passed | Pure/selected unit tests; not Honda integration |
| R-04 | Prior selected donor non-driving tests | 157 passed | Not AGNOS, GUI, phone, StarPort or on-device test |
| R-05 | Latest donor FLM global runtime and pose interval, exact be175 source | **40 passed, 3 warnings, exit 0** | Latest FLM source but host-native support modules from donor 10d17 |
| R-06 | Broader FLM suite on the sparse mixed-source latest worktree | **1 test failed at raw worker** | Worker reported fit_failed; mixed source and process environment prevent regression attribution |
| R-07 | Same raw-worker test in original pinned fully native donor checkout | **1 passed, exit 0** | Does not prove that the full new mixed checkout works |
| R-08 | Earlier latest MVL Params, IPC, VisionIPC and acados/MPC native targets; Dom Params and IPC | Built successfully on x86-64 | No full no-cache release build or ARM64 target proof |
| R-09 | Prior 6-ELF host library audit | No missing linked libraries reported | Host executable dependencies only |
| R-10 | Read-only AGNOS system image investigation | VERSION 19.8.1, hash captured; root accessible | Not booted; several system files produced debugfs short-read errors |
| R-11 | Codex targeted source review | Completed, deployment **HOLD** | Limited to MVL Honda interface and MADS state source |
| R-12 | Direct Windows Qwen2.5-Coder 14B source-excerpt review | Completed, limited/truncated response | Several false or unsupported allegations; not a safety signoff |

The fresh R-02 native command, from the separate MVL Ubuntu workspace and its pinned native Python environment, selected these modules: MADS state machine; MADS steering mode; lateral torque buffer; and opendbc Honda safety tests. Full stdout/stderr and the exit code are preserved in [mvl_current_targeted_safety_rerun_20261103.log](evidence/mvl_current_targeted_safety_rerun_20261103.log). R-01 and R-02 overlap and must **not** be added for a unique test count. The 612 skips remain unexecuted, including inherited safety-test skips; do not convert them to passing tests.

R-05 loaded both changed FLM modules directly from the detached be175 temporary worktree, as recorded by their module paths in [latest_dom_flm_timing_20261103.log](evidence/latest_dom_flm_timing_20261103.log). The two test files were also taken from this newest pin. The old donor host-native libraries were reused only for compatible source-independent dependencies. R-05 is **not** a full clean be175 build.

R-06 was deliberately attempted to expand coverage. Test test_actual_raw_registered_worker_report_reaches_controls returned fit_failed under the sparse hybrid source setup. That failure must be retained, not discarded or misreported as a new feature defect. The original donor's corresponding test passed (R-07), so there is not enough evidence to isolate a product regression. **Next gate:** clean complete be175 environment, rebuild native dependencies with matching hashes, run the whole FLM test directory including subprocess workers, remove mixed-source imports, and resolve all failures.

## 3. AGNOS, ARM64 and IPC provenance

Read-only debugfs inspection of the available ext4 image shows a root VERSION value of **19.8.1**, and /etc/issue reports Ubuntu 24.04.5. The exact image hash is recorded above and in [agnos_image_readonly_abi_inventory_20261103.log](evidence/agnos_image_readonly_abi_inventory_20261103.log). A short-read error when extracting /etc/os-release and /etc/hostname means those attempts do not provide usable OS/ABI attestation.

MVL binaries in the assessed native workspace (libparams_c.so, ipc_pyx.so, VisionIPC shared library) identify as **ELF x86-64**. A shared library supplied in the separate latest donor worktree identified as **ELF ARM aarch64** and was not loadable into the host Python interpreter. Only in the disposable worktree, its original bytes were preserved as an ARM64-marked backup and host-built x86 library was used to execute R-05. The original qualified donor and MVL controller workspaces were not overwritten.

A successful x86-64 native build demonstrates functioning host source dependencies, **not** compatibility with ARM64 AGNOS 19.8.1, the comma device, boot, GPU model/driver monitoring coexistence, USB projection, physical Panda, or OEM CAN-FD. No ARM64 complete clean cold build or target-device runtime was executed. The Ubuntu engineering volume had approximately **8.4 GB free (91–92% full)**. A full clean target build must use a carefully capacity-planned separate workspace/output disk; historical data should not be deleted automatically.

MVL uses Cython IPC and native message contracts; donor builds nanobind IPC components. Their separately successful host builds do not prove binary interchangeability or safe mixed deployment. Any MVL UI adapter must use typed MVL-native cereal, Params and IPC contracts instead of copying donor generated binaries.

## 4. Independent review results and verification quality

### Codex: completed focused source review

A read-only GPT-5.6 Terra Codex review completed using pinned MVL Honda interface and MVL MADS state code. It returned **HOLD** for live driving integration and identified three material source-level concerns:

1. The MVL Honda interface contains an explicit warning about Bosch alpha-longitudinal radar disable and loss of factory AEB functionality. Retained stock ACC in a prior failed engagement is not proof of collision-mitigation preservation across configurations.
2. CAN-FD radar/ACC handover and diagnostic handling are sequencing-sensitive and include comments describing potential brake-module CRUISE_FAULT when replacement transmissions are delayed. Such comments describe claimed failure conditions and mitigation logic, **not physical test evidence** for this Accord.
3. MADS state transitions among paused, disabled, enabled, and override do not establish Panda permission, Honda steering/brake actuation, OEM radar state, ECU diagnostics, or FCW/CMBS/AEB. Passing MADS tests alone cannot validate an imported Dom AOL controller.

See [codex_targeted_current_review_20261103.md](evidence/codex_targeted_current_review_20261103.md) and the preceding independent [codex_independent_final.md](evidence/codex_independent_final.md). The broader earlier Sol invocation did not complete; do not claim a Sol review PASS.

### Qwen: advisory, factual correction required

A direct Windows-host Ollama run of qwen2.5-coder:14b returned approximately 750 generated tokens, truncated by its configured length. Several apparently high-confidence claims **conflict with source**:

- Accord fingerprint validation **exists** at donor opendbc/car/honda/accord_mvl_stock.py line 7.
- Exact expected Accord safety parameter check **exists** at accord_mvl_stock.py line 12.
- MVL has an Accord 11G configuration branch in opendbc/car/honda/interface.py line 135.
- Donor stock_aol.py handles the Accord-specific fingerprint at line 82.
- Generic feature preference parsing does not itself constitute Honda vehicle safety admission; that must be assessed at the qualified runtime policy/CarParams boundary.

The response therefore proves that model inference ran, **not** that its defects are real or that it independently passed source review. Its verbatim review is retained at [qwen14b_honda_review_raw_20261103.json](evidence/qwen14b_honda_review_raw_20261103.json). Prior OpenCode/Qwen standalone attempts stalled and must remain classified INCOMPLETE, not silently upgraded to source-code signoff.

## 5. All 32 feature families — retained dispositions and test ownership

The authoritative feature-by-feature detail remains in [feature_qualification_matrix_32.csv](feature_qualification_matrix_32.csv), the [November 2 complete report](../../20261102/STAR_PILOT_TO_MVL_COMPREHENSIVE_ASSESSMENT.md), and the [latest source-delta review](../ACCORD11G_STARPILOT_MVL_DEEP_ASSESSMENT_20261103.md). Their evidence must remain pinned to their exact source revision; no entire family is called release-qualified simply because one representative test passed.

**Candidate for a separate, default-OFF non-actuating MVL adapter**: presentation-only onroad UI, themes, device/status views, warning-safe visual overlays, authenticated local read-only Galaxy endpoints, model catalog/status, navigation status, trip visualization, offline replay/trace tooling. For these, preserve MVL native camera, soundd alert priority, message freshness and access boundaries.

**Hardware/bench only**: StarPort, Android Auto projection and GPU rendering, phone companion apps, Bluetooth pairing/keys, Soloist audio, parked Sentry and camera, model runners and JetLink, software/update/power changes, telemetry. These require privacy, authenticated local access, alert preemption, device thermal/power budget, and explicit no-effect on driving services.

**Offline simulation only; do not enable in Honda**: AOL independent-axis control, lane centering curvature injection, FLM/learned torque, automatic SLC cruise target updates, curve-speed actuation, Conditional Experimental/Chill, longitudinal profiles, and any Bosch-C/Panda/ECU-affecting hooks. Source-only policies must not grant live driving authority.

**Excluded**: unrelated manufacturer control adapters and mass replacement of MVL's Honda controllers, CAN/DBC, Panda safety or system management.

## 6. Mandatory gate-by-gate engineering plan

| Priority | Gate, owner and next action | Acceptance needed | Current decision |
|---|---|---|---|
| P0 | FLM exact latest donor, feature lead: rebuild a complete be175 native workspace, including workers | 100% selected latest FLM suite with no unknown worker failure and line-level provenance; fault/clock tests | **OPEN**, narrow 40/40 PASS |
| P0 | MVL/Panda host safety, test owner: rerun after every proposed change and investigate skips | Exact source pin, all intended cases and negative safety policy; no unexamined skip represented as PASS | **HOST PASS**, device HOLD |
| P0 | ARM64/AGNOS, build owner: provision dedicated storage/sysroot and cold compile | Full no-cache build, AGNOS 19.8.1 target ABI, complete native dependency audit, binary/recovery identities | **HOLD / NOT RUN** |
| P0 | Honda ECU and OEM safety, system owner: formally establish stock ACC, radar, FCW/CMBS/AEB, fault response | Qualified vehicle-disconnected bench evidence and later approved protected physical verification | **HOLD / NOT RUN** |
| P0 | Panda hardware, safety owner: exact F4/H7 firmware, harness and safety allowlist identity | Hardware-specific receive/transmit-denial, watchdog, disengagement and recovery results | **HOLD / NOT RUN** |
| P0 | Typed MVL integration adapter, engineer: design MVL-native read-only source/Params/IPC registry | Default OFF, no sendcan/UDS, no unsafe cross-scope Params, stale/invalid source rejection, unchanged MVL driving parity | **NOT IMPLEMENTED** |
| P1 | Galaxy/visual UI, security/UI owner: design local read-only pages first | Authentication/CSRF, parked-only mutations excluded, image/alert priority, failure isolation | **DESIGN/TEST PENDING** |
| P1 | StarPort/JetLink/models/media, device engineer: isolated device hardware evaluation | ARM64 GPU/USB/encoder compatibility, memory/thermal budget, modeld/driver-monitoring/audio coexistence | **BENCH PENDING** |
| P1 | Driving feature studies, controls researcher: compare pure functions to MVL planner and torque | Negative freshness/override/limiter tests, no hardware/CAN outputs, independent code review | **OFFLINE ONLY** |
| P2 | Provenance/CI, release engineer: maintain immutable evidence manifest and complete 32-family test mapping | Full script versions, exact commits and hashes, independent review, honest skip/blocker accounting | **PARTIAL** |

Before live driving intervention, approval must be based on the actual vehicle configuration, qualified safe ECU/Panda procedure, physical OEM evidence, release/rollback provenance, and independently reviewed source. No historical Dom or C6-12 tests substitute for native MVL and actual Honda evidence.

## 7. Findings and unclosed release conditions

The pre-existing [20-item findings register](FINDINGS_AND_ACTION_REGISTER.csv) remains open, including eight P0 findings. The new [incremental action register](incremental_action_register.csv) adds source-pin drift, exact FLM worker gap, x86 versus ARM64 mismatch, Qwen false positives, evidence quality, and disk-capacity planning. None of the current checks changes its unclosed deployment status.

**Final scope decision:** Evidence supports MVL-first planning and beginning *only separately scoped, non-actuating, default-OFF read-only integration engineering*. It does **not** support installing combined StarPilot driving features, enabling Panda or ECU changes, claiming automatic OEM takeover after failure, or calling AGNOS/ARM64/physical Honda validation complete. Vehicle deployment remains **HOLD**.

## 8. New evidence files

- [MVL native targeted rerun](evidence/mvl_current_targeted_safety_rerun_20261103.log)
- [Latest donor FLM targeted PASS](evidence/latest_dom_flm_timing_20261103.log)
- [Latest donor full FLM hybrid test failure](evidence/latest_dom_flm_full_python_suite_20261103.log)
- [Pinned donor raw worker PASS](evidence/pinned_donor_flm_worker_baseline_20261103.log)
- [AGNOS image and host ABI inspection](evidence/agnos_image_readonly_abi_inventory_20261103.log)
- [Codex scoped review](evidence/codex_targeted_current_review_20261103.md)
- [Qwen response with unverified allegations](evidence/qwen14b_honda_review_raw_20261103.json)
- [Latest five-file donor delta](latest_flm_delta_to_be175.csv)
- [New action register](incremental_action_register.csv)
- [Evidence manifest with hashes](incremental_evidence_manifest.json)
