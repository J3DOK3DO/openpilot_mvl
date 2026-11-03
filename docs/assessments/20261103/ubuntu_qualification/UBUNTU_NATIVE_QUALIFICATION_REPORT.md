# StarPilot:Dom to MVL — Ubuntu Native Qualification Report

**Campaign:** UQ-20261103 • **Date:** 2026-11-03 • **Target:** 2025 US Honda Accord 11G Hybrid, Bosch-C/CAN-FD • **Authority:** MVL Honda control architecture

**FINAL CLASSIFICATION: PASS for the specifically executed offline host checks; HOLD for all unimplemented vehicle features, AGNOS/ARM64 deployment and actual vehicle qualification.**

This is the mandatory Ubuntu qualification supplement to the November 2 full-file inventory and the November 3 source delta assessment. It does not restart those audits, replace their evidence, imply that all feature behavior is tested, or certify any vehicle release. No car-facing code, ECU configuration, Honda controller logic, Panda safety code, or physical vehicle was modified.

## 1. Exact baseline and source pinning

| Repository/reference | Exact revision |
|---|---|
| StarPilotHQ/StarPilot, original Dom | 10d170e799aa8d492a3f604ef8e91aafa3c11408 |
| Previous November 3 donor delta audit | 3924bd2e3917731e72012e784879262ca954c7ae |
| November 2 donor baseline | cbd6e1eb52e8a46f9837a750d675b877d5ac8762 |
| mvl-boston/openpilot, sp-honda-dev-202608 | 376c44b5731b2655e5c2f301b73c9729eb499e91 |
| Existing user's MVL assessment branch parent | 7607cf9aa6664f4a31ff611613152c7bc87c6218 |
| mvl-boston/opendbc gitlink | 3fec9a418a659de31d7b1f494193161697a35071 |
| MVL Panda gitlink | 8a16e089b88593914823743df29e1c30b7dd3e00 |
| MVL NNLC data gitlink | 03cac2d30e111e0689c0429cb8c1fe6cb5a905af |

The earlier audit accounted for 9,269 Dom Git entries, expanded to 9,305 in the November 3 audit, with 32 first-party subsystem families. That source inventory and detailed feature descriptions remain valid as *static disposition evidence*, not vehicle safety proof.

An exact new comparison found **nine changed Dom paths** since the November 3 donor pin, concentrated in FLM training reports and Galaxy display/tests plus prebuilt metadata. No Honda controller source was among those nine paths. On MVL, **four changed non-documentation paths** relative to the assessment branch were identified: SConstruct, openpilot/common/scons_cache.py, openpilot/common/tests/test_scons_cache.py and openpilot/system/manager/build.py. See [pinned_source_changes_since_prior_review.csv](pinned_source_changes_since_prior_review.csv) for every path, old/new blob SHA and pinned code link.

The latest MVL source was checked out separately from the assessment branch, so there is no ambiguity between earlier report provenance and tests against the actual newer source.

## 2. Executed qualification and auditable results

| ID | Native check | Outcome | Reproducible evidence |
|---|---|---|---|
| N-01 | Initial MVL MADS, controls and Honda baseline | 92 passed, 1 skipped | evidence/mvl_extended_native_pytest.log |
| N-02 | Earlier pinned MVL Honda safety-policy Python suite | 1,046 passed, 612 skipped | evidence/mvl_honda_panda_safety_pytest.log |
| N-03 | **Latest MVL MADS, controls, Honda, Honda safety and SCons cache tests** | **1,140 passed; 613 skipped; 0 failed** | evidence/latest_mvl_native_combined_pytest.log |
| N-04 | Dom lane-centering, curve-learning, conditional settings, SLC selection, FLM and Galaxy FLM tests | **149 passed; 0 failed** | evidence/latest_dom_selected_feature_pytest.log |
| N-05 | Dom selected audio, model status, Sentry, spot monitor, trace validator, Bluetooth, navigation, software and Galaxy tests | **157 passed; 0 failed** | evidence/latest_dom_nondriving_selected_pytest.log |
| N-06 | Latest Dom Python AST on all tracked Python files | **5,603/5,603 parsed** | static_validation_20261103.json |
| N-07 | Latest MVL tracked Python AST | 810/811 parsed; sole exception is binary-like copyparty-sfx.py | static_check_exceptions.csv |
| N-08 | Dom first-party JavaScript and MJS syntax under Node.js | **200/200 passed** | static_validation_20261103.json |
| N-09 | Latest MVL source-local native Params library | Build succeeded | evidence/latest_mvl_native_params_build.log |
| N-10 | Latest MVL IPC, VisionIPC and longitudinal acados MPC/Cython targets | Builds succeeded | evidence/latest_mvl_native_ipc_build.log and evidence/latest_mvl_native_vipc_acados_build.log |
| N-11 | Dom source-local native Params and nanobind IPC targets | Builds succeeded | evidence/latest_dom_native_core_build.log |
| N-12 | Six host ELF dynamic-library inspections, including hashes | 6 inspected, **zero missing linked libraries** | evidence/native_elf_dependency_audit.log |
| N-13 | Independent Codex review | Completed, material issues identified; **deployment HOLD** | evidence/codex_independent_final.md |
| N-14 | Local Qwen3 8B CPU-mode advisory | Completed; **deployment HOLD** | reviewer_qwen_direct.md |
| N-15 | OpenCode/Qwen standalone session | No reviewer output; stopped only assessment-specific process | reviewer_qwen_direct.md |
| N-16 | AGNOS ARM64 exact build, Panda physical firmware and on-car trials | **NOT EXECUTED** | This report, Section 6 |

The selected Dom N-04 and N-05 test files are distinct and total **306 selected donor unit-test passes**. The older MVL N-01 and N-02 results are historical baseline runs in this campaign and must not be added to N-03 to produce a misleading unique test total. The skipped cases in N-03 are still unexecuted: 544 pytest unittest skips, 51 unsupported user-regen cases, 17 missing second-speed-message cases and one parameterized base class. The test summary preserves all skips.

All compilation was on **Ubuntu x86_64**, using the installed Python 3.12.13 development toolchain and exact source-local native build targets. Several SCons objects came from its content-addressed cache; a full cold/no-cache release build is still required. The donor build used an isolated nanobind 3.1.0 dependency matching its lockfile, rather than modifying another development environment.

### Environment gaps resolved in this qualification

- Original MVL NNLC failure: pinned neural-network-data gitlink was absent in the sparse checkout. Checking out its exact submodule resolved the issue, and the rerun passed.
- Latest MVL imports initially failed because generated Params, msgq IPC, VisionIPC and acados longitudinal MPC binaries were not present. Compiling these targets against latest MVL source resolved collection failures and the expanded regression suite passed.
- Dom initially lacked full sparse-checkout source, rednose SCons tooling and nanobind. These were restored in an isolated donor checkout. Dom IPC and Params targets then compiled and selected feature tests passed.
- Dom native msgq uses **nanobind _ipc.so**; MVL uses **Cython ipc_pyx.so**. Successful separate builds demonstrate a real compatibility boundary and do **not** imply the two IPC implementations are drop-in replacements.
- UI and StarPort selected test collection required **raylib_nb**, absent from the isolated Ubuntu Python environment. No GUI or StarPort runtime PASS is claimed.
- Linux host ELF library resolution does not establish ARM64/AGNOS dependency closure.

## 3. Major architecture and safety findings

### P0 — Honda 11G factory safety and stock ACC ownership

MVL Honda CarInterface and CarController remain mandatory. The pinned MVL Honda code includes alpha-longitudinal configuration and an explicit warning that enabling Bosch custom longitudinal control can disable factory AEB/CMBS functionality through radar disable. A previous case where stock ACC kept working after failed openpilot engagement **does not demonstrate automatic OEM takeover in every failure mode or preserved FCW/CMBS/AEB in every configured mode**. No firmware changes, Panda safety hooks, Honda CAN sends or UDS commands were made in this assessment.

Authoritative Honda interface: https://github.com/mvl-boston/opendbc/blob/3fec9a418a659de31d7b1f494193161697a35071/opendbc/car/honda/interface.py

### P0 — MADS versus StarPilot AOL axis grants

MVL's existing MADS state machine and Dom AOL have different active/paused axis semantics and source/safety receipt requirements. Independent Codex review specifically flagged that MVL's silent LKAS disable may produce **paused**, which is not the same as active steering and not necessarily the same as fully disabled. No Dom alternativeExperience, safety-bit, Panda axis permission or CarParams policy may be transplanted without exact-identity native proof and driver override/fault evidence. Existing MVL MADS tests passing do not qualify a future Dom AOL adapter.

### P0 — Radar, CAN-FD and controller interaction

The Accord Bosch-C CAN-FD implementation has distinct radar/ECU ownership, OEM cruise, LKAS/HUD and diagnostic behavior. Source code includes handover sequences and known risks if timing or release sequencing is wrong. Integration must separately demonstrate correct CarParams and ECU identity, handover ordering, stale CAN rejection, all transmitted-message allowlists, and recovery after service failure. Any such command-path modification remains outside the approved current campaign.

### P0 — SLC, curve, conditional modes, longitudinal profiles and steering FLM

Dom SLC can update Card-owned cruise targets; curve, conditional and profile logic can influence actual longitudinal plans; lane centering and FLM can influence steering. Their **pure numeric functions or selected settings tests may pass** without establishing a safe Honda live integration. Default them **OFF**; permit only read-only visual comparison and deterministic offline simulation until native MVL controls and Honda-specific safety/vehicle evidence exist. The nine newly changed donor FLM/Galaxy reporting files do not prove newly qualified steering behavior.

### P1 — Device, browser, model, data and media boundaries

Galaxy settings, local HTTP auth, phone Bluetooth bridging, StarPort projection, camera/video, modeld/JetLink and Spotify/Soloist rely on resources and credentials currently owned by MVL or AGNOS. These are separate subsystem integrations, not one copyable UI. Require authenticated local access, no mutating action while driving, strict input schema, read-only/default-off implementation, sound warning priority, camera resource budgets, rollback, opt-in data transmission and device-specific memory/thermal tests.

### P1 — Source configuration and Params collisions

The earlier static review identified 254 identical literal settings key names across repositories. Equal names are not proof of equivalent types, authorization, saved defaults, lifetime or migration behavior. Build a versioned typed translation contract. Retain MVL's module, Panda, opendbc gitlink and model artifacts; preserve license notices. Full-repository overlays are prohibited.

### P1 — Source and reviewer limitations

Independent Codex source review has a completed report and a HOLD verdict. An earlier broader Sol session timed out, so it is **not** a formal Sol PASS. Direct Qwen3 8B produced an advisory response; it did not load or independently inspect every source, and certain generic hazard suggestions in its answer are not evidence. OpenCode/Qwen 8B stalled at service startup and was stopped, without touching unrelated sessions. The Windows RTX 4070 had almost no free VRAM during checks, so Qwen3-Coder 30B source-level signoff was not conducted. No installed feature's release-ready signoff has been asserted.

## 4. All 32 feature families — disposition and completeness

The accompanying [feature_qualification_matrix_32.csv](feature_qualification_matrix_32.csv) records **every** first-party StarPilot family with source URL, original disposition, MVL counterpart, native test status, remaining acceptance criterion and priority. A family with one passing representative test is **not** marked completely qualified.

| Family group | Current migration disposition |
|---|---|
| analytics | Defer external statistics/location reporting; privacy, opt-in and egress proof |
| aol | Preserve MVL MADS, study Dom axis policy offline; no live import |
| audio | Adapt sound pack/presentation; retain critical soundd and urgent warnings |
| bluetooth | Isolated offroad pairing and hardware-resource owner testing |
| car | Do not import any Dom brand controller; Honda and Panda stay MVL |
| companion | Separate Android/iOS builds, signing, permission and Bluetooth tests |
| conditional_mode | Offline experimental/chill policy only; no Honda acceleration authority |
| connect | Defer remote network access until security and owner approval |
| controllers | Offline wheel/cruise arbitration research; stock Honda button owner preserved |
| curve_speed | Read-only display/pure geometry studies; no automated speed writes |
| drive_state | Read-only trip/state adapters, freshness and privacy tests |
| favorites | UI/nav preferences mapped to MVL |
| flm | Offline steering learning/report analysis; no live Honda learned torque |
| galaxy | Authenticated local read-only web service first; settings mutation deferred |
| galaxy_bluetooth | Isolated bridge/auth/key test, no general LAN exposure by default |
| gps | Reuse MVL locationd clocks and status |
| lateral | Lane centering and torque methods offline only |
| longitudinal | Planner/brake/stop policy offline only; preserve MVL OEM handover |
| maps | UI/map status and cache visualization; retain MVL mapd |
| models | Catalog/status read-only; modeld ABI, paired lab and JetLink deferred |
| navigation | UI on MVL navd/mapd, no competing route/speed owner |
| power | Preserve MVL shutdown, thermal and battery policy |
| replay | Offline tooling only; no replay equals car evidence |
| sentry_mode | Parked camera/alert bench only with privacy, power and consent |
| software | Read-only software status; updater/rollback mutation deferred |
| soloist | Hardware sound bench; never block urgent driving alerts |
| speed_limits | Advisory UI only; no automatic Honda cruise updates |
| spot_monitor | Visual warning only; never authorize lane change |
| system | StarPort/JetLink hardware and GPU bench; current Raylib test gap |
| ui | Selective native visuals; current Raylib test gap and warning overlay requirements |
| validation | Adopt offline validators without conflating synthetic traces with certification |
| tests | Port relevant regression evidence per owning module, with exact source pins |

## 5. Review status and source-specific acceptance

The independent Codex review confirmed a **HOLD** for deployment and identified source issues not resolved by passing tests: alpha-long OEM AEB/CMBS behavior, radar handover/DTC recovery and MADS paused versus steering-active semantics. [Read the Codex findings](evidence/codex_independent_final.md).

[Qwen's advisory](reviewer_qwen_direct.md) separately concluded no deployment approval. The direct Ollama result is preserved transparently and must not be described as a complete second independent code review. Independent reviews of **each future implemented adapter** are still required.

## 6. Non-negotiable outstanding gates

| Gate | Current state | Required proof |
|---|---|---|
| Native host compile and selected safety/feature tests | **PASS for named scope** | Re-run after each source/adapter change |
| Full cold build and exact binary supply chain | **OPEN** | No-cache complete build, hash/manifests, reproducible link audit |
| Cross-repo typed settings, IPC, CarParams adapters | **NOT IMPLEMENTED** | Default-off parity tests, schema ownership and stale-data rejection |
| Native UI/Raylib/StarPort graphics and device workload | **BLOCKED/NOT RUN** | Real C3/C4/AGNOS build, GPU/thermal/memory benchmark |
| ARM64 binary and actual AGNOS runtime | **NOT RUN** | Exact target image/sysroot, model/DM coexistence, process lifecycle |
| Actual Panda firmware safety receipt and harness topology | **NOT RUN** | Exact device firmware identity, safety allowlists and negative tests |
| Real Honda OEM stock ACC, AEB/CMBS/FCW and fault recovery | **NOT RUN** | Safe controlled physical test plan with explicit owner approval |
| Independent code safety signoff on ported components | **NOT APPLICABLE YET** | Exact commit PASS only after implementation |
| Installable combined comma branch and rollback drill | **HOLD** | All earlier release gates must be closed |

The current **GO** is limited to starting a separate, non-actuating read-only MVL adapter engineering campaign with every optional feature default OFF. The **HOLD** covers all live driving interventions, safety-policy changes and vehicle installation.

## 7. Artifacts and proof index

- [Qualification evidence summary](qualification_evidence_summary.json)
- [32-family qualification matrix](feature_qualification_matrix_32.csv)
- [Latest source-change register](pinned_source_changes_since_prior_review.csv)
- [Static AST and Node evidence](static_validation_20261103.json)
- [Native latest MVL regression log](evidence/latest_mvl_native_combined_pytest.log)
- [Dom donor driving feature log](evidence/latest_dom_selected_feature_pytest.log)
- [Dom donor non-driving feature log](evidence/latest_dom_nondriving_selected_pytest.log)
- [MVL Params and IPC native build logs](evidence/latest_mvl_native_params_build.log), [VisionIPC/MPC native build](evidence/latest_mvl_native_vipc_acados_build.log)
- [Donor native library build](evidence/latest_dom_native_core_build.log)
- [Native ELF hashes and linked libraries](evidence/native_elf_dependency_audit.log)
- [Independent Codex final findings](evidence/codex_independent_final.md)
- [Qwen review and OpenCode attempt record](reviewer_qwen_direct.md)
- [Prior complete full-feature assessment](../../20261102/STAR_PILOT_TO_MVL_COMPREHENSIVE_ASSESSMENT.md) and [Nov 3 updated source assessment](../ACCORD11G_STARPILOT_MVL_DEEP_ASSESSMENT_20261103.md)
- [Mandatory step-by-step migration qualification plan](MIGRATION_GATE_PLAN.md)

**Engineering conclusion:** We have materially strengthened the prior source inventory with **verified native host and selected donor tests** and explicit independent risk review. That satisfies the named *offline baseline* portion of the mandatory Ubuntu stage. It does **not** satisfy full ARM64, device, Panda firmware, integrated driver-controller or real Honda qualification. Preserve the MVL Honda architecture and do not promote any untested driving feature to a vehicle release.
