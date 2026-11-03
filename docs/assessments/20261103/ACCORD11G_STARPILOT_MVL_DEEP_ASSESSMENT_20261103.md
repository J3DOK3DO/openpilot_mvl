# StarPilot:Dom to MVL — deep feature assessment and current-source delta
**Audit date:** 3 November 2026
**Decision classification:** Static evidence complete for Git-tree path enumeration; feature semantics and independent safety qualification remain conditional.
**Build outcome:** No MVL integration code written. No comma deployment, CAN transmission, ECU flashing or road test.

## Executive decision
Preserve MVL's Honda Accord 11G/Bosch-C CAN-FD architecture as the foundation. StarPilot is a donor for carefully isolated, independently tested features only. The verified baseline preservation boundary includes Honda DBC/CarInterface/CarState/CarController, radar/stock ACC ownership, Panda/host safety, steering-override and CMBS/AEB/FCW state, all existing MVL MADS/longitudinal behavior and saved settings. Porting a feature does not authorize carrying its donor runtime hooks or safety policy into MVL.

## Exact reproducible revisions
- Donor latest **StarPilotHQ/StarPilot:Dom**: 3924bd2e3917731e72012e784879262ca954c7ae
- Previous donor audited source: cbd6e1eb52e8a46f9837a750d675b877d5ac8762
- MVL latest **mvl-boston/openpilot:sp-honda-dev-202608**: 376c44b5731b2655e5c2f301b73c9729eb499e91
- Previous MVL source and current user's fork foundation: a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1
- Honda opendbc pin in original MVL assessment: 3fec9a418a659de31d7b1f494193161697a35071
- The user fork's audit branch is not automatically rebased onto latest MVL; no source files modified.

## Source coverage and reconciliation
| Measure | Count |
|---|---:|
| Total donor paths in previous pin | 9269 |
| Total donor paths in latest pin | 9305 |
| Donor changed path events, explicit add/delete | 838 |
| Changed paths in the starpilot namespace | 192 |
| Changed paths flagged high risk, heuristic | 223 |
| Current first-party code-bearing components, tracked | 1013 |
| First-party code-bearing components newly added | 6 |
| Prior local first-party components with AST/source descriptions | 983 |
| Latest changed source files targeted | 449 |
| Latest changed source files text-inspected | 308 |
| Latest targeted source files not text-inspected | 141 |
| Structural top-level Python symbol changes | 38 |
| Textual runtime-hook candidates (not proven invocations) | 5980 |
| MVL upstream changed paths | 4 |

This latest-register method uses tracked Git paths and exact blob SHAs. The 838 count uses the --no-renames change-event method; the default rename-aware diff reports 837 paths. The initial scan inspected 4,999 of 9,269 old donor entries; the uninspected entries are transparently retained in the original disposition register. The newest targeted scan inspected 308 of 449 changed code paths, leaving 141 uninspected (44 heuristically high-risk). Absence of a file read, syntax error, or source mention must not be promoted to a clean safety result.

**Important scope correction:** 983 in the previous report was locally inspected first-party code components. The current Git-based component register counts 1,013 tracked first-party source paths. The difference reflects six newly added code paths plus previously tracked paths absent from the earlier sparse/text-inspection population. Neither number means this many user-visible features or independent tests. The 32 family rows below are architectural decisions; the 1,013-row register supplies file-level traceability, not a claim of complete function-level semantic verification.

## Feature family disposition (all 32 first-party packages)
Every disposition below is a **proposed engineering action**, not a port already implemented or qualified.

| Family | Latest code files | Changed paths | Risk | Disposition |
|---|---:|---:|---|---|
| analytics | 6 | 0 | L | DEFER_TELEMETRY |
| aol | 16 | 8 | H | OFFLINE_COMPARE_NO_LIVE_PORT |
| audio | 10 | 0 | M | ADAPT_BEHIND_MVL_SOUND |
| bluetooth | 4 | 0 | M | BENCH_ISOLATED |
| car | 98 | 5 | H | NO_CAR_PORT |
| companion | 65 | 0 | M | OPTIONAL_EXTERNAL_APP |
| conditional_mode | 28 | 0 | H | OFFLINE_SIM_ONLY |
| connect | 3 | 0 | H | DEFER_REMOTE |
| controllers | 11 | 1 | H | OFFLINE_COMPARE |
| curve_speed | 8 | 0 | H | PORT_READONLY_POLICY_OFFLINE |
| drive_state | 4 | 0 | L | PORT_READONLY |
| favorites | 5 | 0 | L | ADAPT_UI |
| flm | 114 | 3 | H | OFFLINE_RESEARCH_ONLY |
| galaxy | 166 | 17 | M | PORT_AUTHENTICATED_LOCAL_READONLY_FIRST |
| galaxy_bluetooth | 12 | 1 | M | BENCH_ISOLATED |
| gps | 6 | 0 | M | COMPARE_AND_ADAPT |
| lateral | 50 | 1 | H | OFFLINE_ONLY |
| longitudinal | 41 | 0 | H | OFFLINE_ONLY |
| maps | 6 | 0 | M | ADAPT_UI_AND_STATUS |
| models | 28 | 3 | H | DEFER_RUNNER_PORT;_UI_FIRST |
| navigation | 13 | 0 | M | ADAPT_UI |
| power | 2 | 0 | H | COMPARE_NO_SYSTEM_POLICY_REPLACE |
| replay | 8 | 2 | L | PORT_DEV_TOOLING_ONLY |
| sentry_mode | 9 | 0 | M | BENCH_READONLY_FIRST |
| software | 6 | 0 | H | STATUS_READONLY_MUTATIONS_DEFER |
| soloist | 16 | 0 | M | BENCH_ISOLATED |
| speed_limits | 21 | 0 | H | UI_ADVISORY_ONLY;_CONTROL_OFFLINE |
| spot_monitor | 7 | 0 | M | UI_READONLY_ONLY |
| system | 63 | 5 | H | BENCH_STARPORT_AND_JETLINK |
| tests | 0 | 6 | L | PORT_RELEVANT_TESTS_ONLY |
| ui | 162 | 139 | M | PORT_SELECTIVE_VISUALS |
| validation | 1 | 0 | L | PORT_TOOLING |

## Functional assessment — actuation-sensitive features

1. **AOL and independent axes:** Axis-grant and latch state must not bypass MVL MADS or its steering authority. Compare preconditions and transitions offline; no live Honda host or Panda permission import.
2. **Lane centering, smoothing and lane changes:** Dom's bounded curvature and Ioniq-tagged injection cannot be assumed Honda-compatible. Compare MVL trajectory, torque, override, stale-source and lane-change policies in a pure replay harness. Visuals may be ported separately from actuation.
3. **FLM/Auto Learn/torque tuning:** Dom has new Galaxy training-result and saved-preference surfaces; its training and controller bindings require exact vehicle/model/source-time provenance. MVL's native torque extensions and NNLC remain source of truth. No learned coefficients written to live Honda steering before safety review.
4. **Longitudinal, curve and conditional policies:** Any planner, coast, brake or speed-target write is a control change; keep simulator-only. Factory ACC/CMBS/AEB/FCW invariants require exact hardware modes and physical qualification.
5. **SLC/speed source fusion:** Differences between dashboard, map and vision readings can be safely displayed as advisory only after units, freshness, attribution and disagreement tests; automatic vCruise or button writes are blocked.
6. **Wheel buttons and cruise helpers:** Buttons/SET/RES/CANCEL are OEM authority interfaces, not simple UI interactions. Preserve MVL button arbitration, fail-closed conditions and onroad behavior.
7. **Blindspot/V-ASM:** Video-based spot monitoring may only render a non-certified informational overlay; it cannot assert clear adjacent-lane authority or enable lane change.
8. **Vehicle adapters and Panda:** All Dom other-make code excluded from Honda builds; Dom's Honda helpers and Panda safety remain comparison-only. A passing non-Honda test is no Honda evidence.

## Functional assessment — display, media and services

1. **Native UI, C3/C4, SpacePilot layout and Raylib:** Selective assets/geometry via MVL-native read-only adapter. Latest raylib bridge adds a compiled native extension; verify ABI, licensing, drivers, device GPU costs, camera and warning priority. Do not replace MVL selfdrive/ui as a wholesale directory.
2. **Galaxy:** The donor manager registers Galaxy and multiple process helpers. process_config's galaxy_local predicate runs unless STARPILOT_GALAXY_DISABLE=1; this is not a safe default-off integration assumption. Server contains device settings, software operations, local access, pairing, camera/recordings, route/log management, controller actions and remote pairing. Start from an authenticated, locally bound, default-OFF, read-only allowlist rather than copying the server and disabling a handful of routes.
3. **StarPort/Android Auto projection:** Separate projection engine, APK identity/import, USB/Bluetooth, media, GPU encoder and headless EGL concerns. Require isolated lab validation of device exclusivity and modeld/driver-monitoring scheduling before any onroad deployment.
4. **Bluetooth/phone companion/soloist:** Separate LAN, pairing, key management, Android/iOS signing, A2DP and Spotify Connect. Alerts/soundd must retain highest priority; project is optional device qualification.
5. **Model manager, runtime recovery and JetLink:** MVL owns modeld and AGNOS artifact ABI. Adapt catalog/status first; no new model runner, JIT, remote model selection or fallback integration without CPU/GPU native builds and exact model output checks.
6. **Maps/navigation/GPS/favorites:** MVL navd/mapd and location timestamps remain authoritative. Selectively port design and read-only summaries; no duplicate data download/database owner.
7. **Analytics, drive state, replay, sentry and power:** Consent, local retention, privacy, parked/offroad authority, recording exposure and thermal/battery constraints determine whether these optional services may run.
8. **Software updates, recovery and connectivity:** No remote branch install, restart, flash or delete operations through Galaxy until authentication, approvals, known-good boot slot, recoverability and signed provenance are independently proved.
9. **Settings, themes and audio:** Dom manager executes startup state migration, retirement, sound enrollment and cloud activation. Never copy this path into MVL. Namespaced settings adapter and snapshot/restore must preserve MVL keys, calibration, alert semantics and user preferences.

## Verified specific code-boundary findings at latest donor SHA
1. **process_config.py process predicate** — galaxy_local returns true unless an explicit disable env var exists; not automatically opt-in; also declares starport/spotify/jetlink functions. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/system/manager/process_config.py#L76-L97).
2. **process_config.py managed daemon list** — Galaxy and multiple persistent companion/sentry/projection services are registered as native manager processes. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/system/manager/process_config.py#L139-L170).
3. **manager.py startup migrations** — prepare_manager_start(auto_migrate=True), external preference reset, settings retirement, default sound enrollment and cloud-provider activation happen during manager_init. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/system/manager/manager.py#L25-L66).
4. **manager.py parameter initialization** — Dom loops through all Params defaults and writes missing values; MVL persistence must not be replaced. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/system/manager/manager.py#L74-L101).
5. **Galaxy server import surface** — Server composes mutation-capable settings, device, software, map, recordings, controller and connectivity endpoints. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/starpilot/galaxy/server.py#L17-L65).
6. **Galaxy local server default** — make_server is default-bound to 127.0.0.1:8082 but remote/phone/hotspot proxy owners require independent checks. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/starpilot/galaxy/server.py#L82-L105).
7. **FLM saved state provenance** — Training-result preference reads CP and persisted params with stale/value checks; mapping to MVL CP formats is required. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/starpilot/galaxy/flm_training_results.py#L21-L57).
8. **Raylib native extension** — A direct raylib_nb native backend + _raylib_extra extension dependency exists; cannot assume AGNOS ABI. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/starpilot/ui/raylib.py#L1-L8).
9. **Honda Panda safety status change** — Changed code indexes rx_status by Honda workspace index rather than legacy inline RxCheck status; safety semantics require separate Panda review, no transplant. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/opendbc_repo/opendbc/safety/modes/honda_stock_aol.h#L91-L170).
10. **General Honda Panda change** — Several transmit message arrays become const; not evidence of Accord safety compatibility. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/opendbc_repo/opendbc/safety/modes/honda.h#L350-L485).
11. **Core controlsd modification** — Angle steering saturation now delegates to Tesla-specific cooperative saturation helper in angle-control branch; must not be merged wholesale into MVL. [Pinned source](https://github.com/StarPilotHQ/StarPilot/blob/3924bd2e3917731e72012e784879262ca954c7ae/openpilot/selfdrive/controls/controlsd.py#L548-L570).
12. **MVL upstream SCons cache change** — Newest MVL adds interrupted-build cache recovery, not new Honda controller authority. [Pinned source](https://github.com/mvl-boston/openpilot/blob/376c44b5731b2655e5c2f301b73c9729eb499e91/openpilot/common/scons_cache.py).

## Evidence gaps that block declaring a complete *verified* feature assessment

- All 9,305 latest Dom paths are enumerated; the uninspected 141 changed code paths, including 44 heuristically high-risk paths, remain source/semantic gaps. Some are Panda internals and generated Cap'n Proto headers; no green label is assigned to these.
- The 1,013 source-file rows have family-level dispositions; they have not each received manual behavior or call-chain sign-off. The 5,980 runtime references are search hits and include false positives.
- Feature package count is not the same as end-user subfeature count. Untracked runtime imports, generated binaries, dynamic reflection, native symbols, asset-only configurations and external services require additional tracing.
- Prior first-party file descriptions are derived from AST and first module docstrings, not cross-branch functional equivalence. Shared 254 Params literal strings require type/default/lifecycle checks, not only name matching.
- **Independent agent review:** attempted OpenCode Sol and Qwen3-Coder30B sessions, no usable output produced. Zero independent reviewer PASS. The user's Ubuntu device was offline; native ARM64/AGNOS build, Panda host/firmware tests and camera/network/device bench were not executed.
- The newest MVL upstream advanced four changed files. The user's audit branch still rests on older MVL SHA; rebase or integration should be a separately reviewed change, not a silent source update.
- The exact Honda CMBS/AEB/FCW and stock ACC fallback cannot be inferred from an observed factory ACC recovery after Dom's engage failure.

## Go/no-go by category and acceptance test

| Category | Assessment decision | Minimum evidence to implement |
|---|---|---|
| UI design/colors/geometry | CONDITIONAL GO for offline adapter | MVL-native renderer, warning precedence, DPI/rotation, memory/CPU/GPU perf |
| Galaxy read-only status | CONDITIONAL GO, default off | Local bind, auth allowlist, CSRF/remote/proxy denial, low resource impact |
| Galaxy write endpoints/OTA | HOLD | Parked authority, signed update/recovery, credentials and rollback |
| Audio themes | CONDITIONAL GO | Soundd preserves FCW/AEB/urgent warnings, timing and mute failure |
| Navigation/maps | CONDITIONAL GO for read-only | Preserve MVL nav/map owner, stale source, coordinate and units |
| Model catalog/status | CONDITIONAL GO for display | No changes to modeld, safety consumers, runner ABI |
| StarPort, Bluetooth, phone & Spotify | BENCH ONLY | C4 hardware drivers, USB/GPU, pairing/auth, audio priority, thermal |
| Sentry/camera/analytics | HOLD for privacy review | Data consent, security, parked state, battery/resource evidence |
| Steering/AOL/FLM/lane change | NO LIVE HONDA PORT | Exact CP, torque limit, OEM safety, driver override, native build and instrumented bench |
| SLC, curve, CEM, longitudinal | NO LIVE HONDA PORT | Stock ACC/CMBS/AEB/FCW ownership; planner/native/Panda fault paths; new evidence |
| Dom Honda / other-make adapters / safety | EXCLUDE | MVL source authority retained; separate Honda-specific redesign only |
| Source-tooling/replay | GO in offline development | Provenance, deterministic test and non-transmit conditions |

## Recommended migration sequence, in priority order

**Gate 0: Complete source-evidence closure.** Triage all 141 latest changed code text-exceptions (prioritize 44 high), verify 32 families and all new subfeatures, independently inspect startup/manager/schemas and release tools; establish pin and diff integrity. Repeat independent Sol + Qwen review with actual completed output and actionable findings. Protect MVL Honda files and params before any feature changes.

**Gate 1: Typed MVL compatibility boundary.** Build read-only vehicle/status/Params adapters and a default-OFF registry. Introduce no Panda, DBC, controller, sendcan, steering, cruise or update hooks. Require a test where all optional features OFF is behaviorally identical to the pinned MVL baseline.

**Gate 2: Isolated non-driving UI.** Visuals, read-only overlays, warning-safe audio, navigation presentation and local Galaxy allowlist, each behind a separate feature flag with negative auth and freshness tests.

**Gate 3: Optional platform services on bench.** StarPort and multimedia, phone companion, Bluetooth, model catalog and parked sentry after device/ABI/security/resource qualification.

**Gate 4: Offline driving research only.** Compare Dom and MVL lane centering, FLM, MADS/AOL, speed-limit fusion, curve and long policies under native deterministic faults; no Honda actuation until dedicated qualification.

**Gate 5: Native and physical qualification.** Exact ARM64/AGNOS build, dependency checks, Panda safety tests, CMBS/AEB/FCW and OEM fallback tests, bench resource checks, recovery/rollback, independent review. This work is **not completed** by this documentation audit.

## Evidence files
- Original pinned 2026-11-02 comprehensive report and 9,269-path full register under docs/assessments/20261102.
- latest_dom_delta_register.csv: every changed donor path with old/new SHA, family, risk, exact link and proposed disposition.
- latest_mvl_delta_register.csv: all four newer MVL paths.
- latest_first_party_component_register.csv: every one of 1,013 latest tracked first-party code paths and evidence URL, with prior AST description where available.
- latest_first_party_component_delta.csv: six newly tracked first-party source components.
- latest_first_party_family_counts.csv: family counts and changes.
- latest_python_symbol_delta.csv: structural symbol changes in text-read latest files.
- latest_runtime_hook_candidates.csv: 5,980 line-level candidate references (not independently proven runtime edges).
- latest_source_text_exceptions.csv: 141 source-uninspected/latest parse exceptions.
- audit_latest_delta.py: reproducible read-only scanner and source SHA identification.
- latest_delta_summary.json: counts and exact revision pins.

**Final status:** End-to-end file-level tracking and updated feature-family dispositions completed; manual semantic sign-off for every function, Sol/Qwen independent assessment, native build and physical Honda qualification NOT complete. These cannot be represented as PASS.
