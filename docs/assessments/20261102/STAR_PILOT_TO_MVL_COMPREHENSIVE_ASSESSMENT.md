# StarPilot:Dom → MVL Honda Accord 11G — Comprehensive Feature Engineering Assessment
**Assessment date:** 2 November 2026
**Status:** Completed source-tree, static architecture, component, and migration-disposition assessment. **Not a completed independent AI review, Linux-native build, vehicle safety validation, or release qualification.**

## 1. Executive disposition

**Decision: MVL-first is architecturally preferred for this Honda Accord 11G Hybrid Bosch-C/CAN-FD development.** Preserve mvl-boston/openpilot sp-honda-dev-202608 and its matching mvl-boston/opendbc Honda controller as the authority. Selectively adapt non-driving StarPilot features into isolated MVL UI/services; study any driving behavior offline before proposing Honda-specific runtime hooks. Do **not** replace MVL opendbc, Panda, card/CarState/CarController, radar ownership, disengagement handling, or saved Honda control policy with Dom implementations.

The review is structured to account for the whole StarPilot tree, not only named features. However, 4,270 entries are not locally text-inspected, and runnable cross-architecture qualification remains pending. Every static decision is provisional until the stated acceptance evidence exists. Publishing the assessment branch does not make it an installable vehicle branch.

## 2. Immutable provenance and repository identity

- StarPilotHQ/StarPilot branch **Dom**, pinned SHA: cbd6e1eb52e8a46f9837a750d675b877d5ac8762.
- mvl-boston/openpilot branch **sp-honda-dev-202608**, pinned SHA: a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1.
- MVL opendbc Honda source: mvl-boston/opendbc commit 3fec9a418a659de31d7b1f494193161697a35071.
- Owner workspace: J3DOK3DO/openpilot_mvl, branch accord11g-mvl-starpilot-selective-port-20261102. No original branch was overwritten.
- Source checkout Dom: D:\Dom 7.0\StarPilot-Dom-Assessment-20261102 (detached pinned SHA).
- Source checkout MVL: D:\Dom 7.0\MVL-StarPilot-SelectivePort-20261102.
- This report, file manifest, and script are auditable at docs/assessments/20261102/ in the owner assessment branch.

No C6-12, C7, or former Dom7 generated tests have been treated as production Honda qualification evidence.

## 3. Inventory completeness and static evidence

| Population | Count | Interpretation |
|---|---:|---|
| Dom Git tree entries reconciled | 9,269 | Complete pinned tree path/SHA accounting |
| MVL Git tree entries reconciled | 1,651 | Pinned upstream source baseline |
| Dom only, by same relative path | 8,052 | Includes vendor, assets, tests, platform modules |
| Same relative path but different | 582 | Requires selective diff assessment |
| Identical path+mode+SHA | 635 | Preserve MVL without duplicate integration |
| MVL-only paths | 434 | May disappear in indiscriminate copy/replacement |
| Locally text-inspected Dom files | 4,999 | Syntax/content/keyword scan where checked out |
| Not text-inspected Dom files | 4,270 | Binary, vendor omitted by sparse checkout or unsupported text |
| Folders/module-family buckets | 684 | Fine-grained grouping; *not* 684 validated features |
| First-party StarPilot subsystem directories | 32 | All receive explicit family disposition |
| First-party source components indexed | 983 | Code-bearing non-test modules, per-file paths and symbols |
| Test/fixture files inside first-party families | 1,569 | Presence does not mean execution |
| Changed control/safety or runtime-review paths | 1,302 | Includes test paths; *not* individual defects |
| Non-feature-namespace StarPilot references | 1,378 | Textual occurrences, not necessarily active calls |
| Literal Dom settings references | 3,870 | Evidence sightings, not schema semantics |
| Shared literal Params keys between Dom/MVL | 254 | Potential semantic/schema review; NOT confirmed collisions |

**Invariant**: the 9,269 Dom entries are each represented in dom_full_file_disposition.csv. Each file has its exact blob SHA, path-to-path MVL status, provisional disposition, inspected yes/no, and direct pinned source link. Unreviewed assets and vendor files remain visible rather than disappearing from scope.

## 4. Vehicle architecture boundary: non-negotiable

MVL Honda Accord 11G is not simply a generic Bosch Honda. Its Honda Bosch-C/CAN-FD firmware, steering, radar ownership, CAN-FD HUD multiplexing, lane-path/object rendering, cruise lifecycle, DBC selection, and device/Panda contracts are interdependent.

Dom Honda comparison yielded 16 Python files: 7 common-name source differences, 8 Dom-only helpers, 1 identical initializer. Dom's Honda interface rejects Bosch-C alpha longitudinal in normal release; MVL's Honda interface exposes a different alpha-long availability policy. MVL explicitly warns that turning on alpha longitudinal can remove CMBS, AEB and FCW. Therefore a test where **stock ACC was still functional after Dom engagement failed does not prove universal automatic OEM fallback**, nor does it prove full factory collision-mitigation availability in other configurations.

Specific references:
- https://github.com/StarPilotHQ/StarPilot/blob/cbd6e1eb52e8a46f9837a750d675b877d5ac8762/opendbc_repo/opendbc/car/honda/interface.py
- https://github.com/StarPilotHQ/StarPilot/blob/cbd6e1eb52e8a46f9837a750d675b877d5ac8762/opendbc_repo/opendbc/car/honda/stock_aol.py
- https://github.com/StarPilotHQ/StarPilot/blob/cbd6e1eb52e8a46f9837a750d675b877d5ac8762/opendbc_repo/opendbc/car/honda/accord_mvl_stock.py
- https://github.com/mvl-boston/opendbc/blob/3fec9a418a659de31d7b1f494193161697a35071/opendbc/car/honda/interface.py
- https://github.com/mvl-boston/opendbc/blob/3fec9a418a659de31d7b1f494193161697a35071/opendbc/car/honda/values.py

Dom's specialized stock Accord helper qualifies an exact CarParams safety word and modifies LKAS button messaging. That path is not an acceptable substitute for MVL's full controller. Dom's stock AOL identity and axis grant state cannot be transplanted over MVL's MADS without final CarParams, panda permission, physical-withdrawal, button, and failsafe evidence.

**Protected paths**: MVL opendbc/car/honda/*; opendbc/sunnypilot Honda extensions; opendbc CAN-FD DBC and firmware identifiers; Panda board/safety; openpilot/selfdrive/car; controls, selfdrived and radar/planner safety control; message schemas and release/boot pipeline. Exact Dom code can be used for offline comparison and diagnostics only until an explicit reviewed, bounded adapter qualifies it.

## 5. Feature-family coverage — all 32 first-party packages

Decisions below are engineering dispositions; the per-source-component and per-file CSVs provide traceability for each family.

| Dom subsystem | MVL-first disposition | Rationale / constraint |
|---|---|---|
| analytics | Defer telemetry | External post-drive usage/location reporting needs explicit consent, security and egress controls |
| aol | Offline study; no live port | Independent axis grants, safety latch and stock ACC ownership differ from MVL MADS |
| audio | Adapt behind MVL soundd | Alert severity, mandatory warning volume and callback timing must remain intact |
| bluetooth | Isolated device bench | Pairing, owner and service competition with MVL stack |
| car | No vehicle adapter import | Honda control stays MVL; all non-Honda vehicle-specific adapters excluded |
| companion | Optional app workstream | Android/iPhone source, BLE, app signing, permissions, store ownership |
| conditional_mode | Offline simulation only | Experimental/Chill authority, current source freshness, longitudinal permission |
| connect | Defer external connectivity | Remote authentication, pairing, transport and secret scopes not reviewed |
| controllers | Compare offline | Wheel buttons, coast, cruise action and OEM stock target arbitration |
| curve_speed | Offline policy; advisory UI | Learned comfort may be studied; planner/ACC output prohibited pending qualification |
| drive_state | Read-only port | Trip and engagement statistics; no actuation |
| favorites | Adapt UI | Reuse MVL navigation and saved settings |
| flm | Offline steering research | Ioniq-specific surface learning; no approved Honda torque policy |
| galaxy | Local read-only first | Authenticated Vue pages and API; defer settings mutation, updates and remote sessions |
| galaxy_bluetooth | Isolated bench | Shared pairing credential, GATT proxy, local discovery and LAN bridge |
| gps | Compare existing owner | Use MVL locationd/mapd timestamps and fail-closed stale data |
| lateral | Offline only | Curvature host, lane evidence, controller choice and torque learning are not Honda-qualified |
| longitudinal | Offline only | Speed and braking ownership is incompatible without Honda-specific safety proof |
| maps | Adapt UI/status | Retain MVL mapd cache/data provider and update service |
| models | UI/status first; runner deferred | Native ABI, GPU, firmware, kernels, modeld and fallbacks require device verification |
| navigation | Adapt UI | Reuse MVL navd, routes and map sourcing |
| power | Compare, no policy replace | Device uptime, thermal, power retention and parked resource owners |
| replay | Offline tooling | Reuse validators without elevating replay to production evidence |
| sentry_mode | Parked bench only | Camera privacy, motion detection not physically qualified, resource/battery load |
| software | Status read-only | Keep MVL update/boot/rollback; block install/delete/branch-change API initially |
| soloist | Audio bench | Spotify Connect, phone A2DP, PulseAudio and BlueALSA interaction |
| speed_limits | Advisory UI; control offline | SLC writes card vCruise and cannot be presumed safe under stock Honda ACC |
| spot_monitor | Read-only visualization | Vision warning is NOT a certified blindspot sensor or lane-clearance grant |
| system | Bench StarPort/JetLink | USB, EGL/GPU/encoder, projection, device resource and trust boundaries |
| ui | Selective visual port | Native UI onroad/home/settings, assets and layouts, MVL camera/alerts kept |
| validation | Port offline tooling | Control-mode evidence schema and tests only; not a release certificate |
| tests | Relevant test adaptation | Never treat synthetic tests as on-vehicle or Panda evidence |

All family rows have source evidence in feature_family_review.csv. The 983 first-party code components have individual path, source link, symbol/docstring and family disposition in source_component_review.csv. These are indexed static components, **not 983 individually executed tests**.

## 6. Driving feature findings at sub-feature depth

### 6.1 AOL, MADS and independent lateral
Dom has a typed axis owner, CarParams qualification, saved intent, button events, native Panda axis acknowledgments, and Honda-specific stock adapters. MVL has its own MADS state machine. Dom's Accord 11G stock qualification accepts only exact safety configurations, and stale/withdrawn authority is a safety issue. Keep MVL baseline; compare event/intent/axis state machines offline; do not copy alternativeExperience, Panda safety flags or controller hooks. Establish agreement across physical ACC withdrawal, brake, permanent/temporary steering fault, stale CAN, restart, manual selection and current firmware before any Honda live proposal.

### 6.2 Lane centering, boundaries and lane changes
Dom's lane_centering.py offers bounded correction, confidence thresholds, gap checks, single-line/edge treatment, offset and driver override. Runtime injection is independent of the pure numeric helper and currently carries vehicle-specific gating. MVL already has lane-change behavior, torque extension and steering-adjacent logic. Implement an offline compare harness first; do not publish a curvature correction to Honda controlsd until exact actuator limits, control axis, source freshness and driver disengagement tests pass. Never treat spot_monitor as adjacent lane clearance.

### 6.3 Torque control, FLM, gains and steering learning
Dom contains lateral torque/parameter selection and FLM learning with Ioniq-specific reconstruction. MVL has its own latcontrol_torque_ext, NNLC, jerk-aware and override variants. Controller selection and dynamic learned parameters are not a copy operation. Compare bounded formulas against MVL torque and Honda EPS response separately; do not enable learned Honda torque before native Panda, host-limit and driver-override qualification.

### 6.4 SLC and automatic speed targets
Dom SLC selects Dashboard/Maps/Vision sources, offsets and candidate limits, then sends qualified Card updates to vCruise. Its own documentation says it is not a planner ceiling. MVL has speed-limit and smart cruise subsystems. Preserve OEM stock ACC ownership, visual display and manual SET/RES behavior; port only advisory/status and pure limit interpretation initially. Honda cruise-button and target writes stay blocked pending firmware/ECU authority evidence.

### 6.5 Curve, profiles, conditional and longitudinal planner
Dom includes learned curvature comfort, advisory/curve speed shaping, selected longitudinal profiles, Conditional Experimental Mode and Conditional Chill Mode with source-freshness and axis authority rules. Some live paths are specifically Ioniq-6 or GM-qualified. These are separate from merely displaying a curve; activating planner acceleration or personality logic could change braking/following. Map to MVL's existing planner and smart cruise and preserve stop priority, lead, driver override, stock collision mitigation and fault response. No Honda live port on these findings.

### 6.6 Vehicle settings and wheel owners
Dom has typed settings editors, protected defaults, cross-thread caching, owner revisions, wheel-button gesture mapping and saved schema migrations. MVL has existing Params semantics and Honda custom cruise. Shared literal key strings alone do not prove the same type/meaning: 254 overlap in static search require schema-by-schema reconciliation. Build a namespaced, read-only translation layer; never bulk-copy Params, CarParams, caches or settings defaults.

### 6.7 Driver assistance presentation
Dom can show lane tracking, path, lead, cornering feedback, enhanced steering cues, vehicle/traffic widgets, side-camera PiP and V-ASM spot warnings. MVL also supplies CAN-FD lane path and HUD object support. Read-only displays may be adapted, but source and coordinate transformations must be cross-checked. Retain factory signals and warning priorities.

## 7. Non-driving feature findings at sub-feature depth

### 7.1 Native UI and artwork
Dom native UI includes C3 full-size and C4 compact layouts, home, onroad overlays, wheel controls, themes, lane colors, speed gauges, mini-widgets, settings pages, translation, previews, Bluetooth and multimedia. Use a presentation-only adapter around MVL's event/status schemas; check GPU overlays, scaling, click targets, warning dominance and AGNOS device constraints. Do not replace MVL's entire selfdrive UI.

### 7.2 Galaxy browser studio
Galaxy is a Vue browser companion served locally on port 8082, with settings, device status, statistics, plots, drives/recordings/replays, crash exploration, map status, model control, localization, software controls, Wi-Fi/hotspot, camera/sentry, StarPort setup and phone bridge endpoints. Start with read-only and authenticated local binding. Remote tunnels/account pairing cannot be assumed available. Mutating actions need parked authority, API input bounds, CSRF/session testing and audit logging. Galaxy settings source includes conditional, long, wheel, torque, data, power, PIP, V-ASM and developer confirmation flows — these are distinct capabilities, not a single feature.

### 7.3 Android Auto/StarPort
StarPort includes managed projection service, decoder/encoder, Android APK import, identity and installation, USB/Bluetooth setup and Galaxy/native controls. Its EGL/GPU encoder and low-latency media routing require isolated C4/AGNOS bench, explicit USB ownership and fail-silent behavior while onroad. It must not compete with MVL modeld camera inference, driver monitoring or safety-related processes. Distinguish host-unit projection from phone companion applications.

### 7.4 Android/iPhone companions and Bluetooth bridge
Galaxy mobile apps are separate Android and iOS build/signing targets, sharing BLE pairing and local web assets. The companion phone bridge proxies authorized requests to local Galaxy; web-manifest caches and keys are security sensitive. App signing and real-device Bluetooth/CarPlay tests are not performed by a Windows repository scan.

### 7.5 Model Manager, JetLink and Model Lab
Dom supports verified model downloads, favorites, version/catalog management, runtime load receipts and optional remote JetLink. MVL already has a model manager, modeld_v2, native model artifacts and safety-critical model output consumers. Do not replace MVL's runner, model manifests, Tinygrad, camera processing, compiler ABI or fallback. Dom's paired AMD Model Laboratory is expressly NOT integrated into production modeld; separate artifact integrity, memory, inference timing, freshness, and driver monitoring evidence are needed.

### 7.6 Sound and media
Custom sound packs and 7 alert-volume families, Galaxy phone A2DP, Soloist/Spotify Connect and projection PCM all contend for audio resources. Keep stock immediate-warning audio dominant; prioritize alarm/vehicle safety playback and ensure media cannot suppress it. Validate hardware codecs, PulseAudio and BlueALSA on device before integration.

### 7.7 Sentry, camera and spot monitor
Sentry parked motion, push integrations, crash/media recording, local cameras and V-ASM visual adjacency are different privacy and safety zones. Parked occupancy, sensor ownership, battery and media retention require owner opt-in. Dom documentation admits motion detection is not yet physically qualified. The vision spot output must never be used to override MVL blindspot information or permit lane change.

### 7.8 Telemetry, connectivity, storage and power
Analytics documentation describes external usage reporting with coarse region; review consent, domains, what is sent and disable behavior before adoption. Device power cutoff, hotspot, Bluetooth, updates, saved artifacts/caches, crash reports, and remote networking add new attack and recovery surfaces. Preserve MVL baseline process supervision, offline start behavior, OTA and rollback. Do not accidentally make Galaxy availability a manager or controls prerequisite.

### 7.9 Developer evidence and testing
Dom includes logging, route/segment analysis, replay, validator schemas, module tests, fixture generators, CI, lint and native build support. Reuse pure read-only validators, but avoid accepting tests written for different brands, historical routes or synthetic traces as Honda safety proof. The evidence validator explicitly does not qualify releases.

## 8. Source validation and actual execution

Windows host, **Python 3.13 AST parse only**:
- Dom openpilot Python files present: 2,891; parsed successfully 2,891; zero syntax failures.
- MVL openpilot Python files present: 751; parsed 750; one UTF-8 decoding failure in third_party/copyparty/copyparty-sfx.py, a self-extracting binary-like asset, not demonstrated executable syntax breakage.
- Source-level Honda crosswalk: 16 Dom files, 7 common-name differences, 8 Dom-only, 1 identical.
- Literal Params overlap: 254 keys, each requires type/default/owner review.

**Not performed or passed**: Python imports/linking, pytest/hypothesis execution, AGNOS ARM64 build, native model/gpu tests, Panda build/safety matrix, hardware bench, CAN/UDS testing, physical OEM-AEB/CMBS check, route replay qualification, car-device install, or code-independent PASS. No live vehicle writes occurred.

**Independent AI attempt**: OpenCode Qwen3-Coder 30B and OpenCode OpenAI Sol access were invoked. The invocations did not produce a model response or auditable review. Direct Ollama fallback was also nonresponsive. These assessment-only test processes were stopped; existing unrelated OpenCode service sessions were not terminated. This is a **review blocker**, not a PASS.

## 9. Strict integration order and acceptance gates

| Gate | Deliverable | Mandatory acceptance to advance |
|---|---|---|
| A0 — Baseline and source inventory | Pinned MVL/Dom source, exact file manifest, protected list, family and component catalog | All source paths accounted, MVL git clean, source coverage reconciles |
| A1 — Isolation and schema adapter | MVL read-only service/Params/CarParams adapter, no actuation | Type/schema/version/freshness/identity tests; default OFF |
| A2 — Presentation | Native onroad/home visual integration and read-only warnings | Pixel/alert precedence, touch and device UX benchmarks |
| A3 — Galaxy local service | Authenticated local read-only Galaxy, logging and status | Port/bind, CSRF, auth, message ownership, no drive interference |
| A4 — Multimedia/offroad | Bluetooth, sounds, phone companion, StarPort lab | Audio alerts, USB, GPU, memory/thermal, C4/AGNOS isolated hardware |
| A5 — Offline driving engineering | Lane-centering, SLC, curve, profiles, FLM/controller research | MVL-native unit and simulation suite, source+fault matrices; no CAN sends |
| A6 — Independent safety and native qualification | Codex Sol + Qwen source review, Linux native build, Panda and hardware isolation | Independent PASS on exact commit, negative fault coverage, recovery, state ownership |
| A7 — Candidate release only if approved | Reviewed integration branch, rollback and installation provenance | Honda parked/bench evidence, software/firmware identity, preserved OEM boundaries |

Hold any step that changes hardware, OEM ECU state, Panda permissions, steering, longitudinal targets, driver override or warning priority without the vehicle-specific evidence. Ubuntu being offline means A6/A7 cannot be satisfied in this session.

## 10. Mandatory safety and failure matrix for later engineering

Test each feature in original MVL and in the proposed adapter default OFF/ON for: stale/malformed CarParams, wrong VIN/fingerprint, Bosch-C routing mismatch, fake safety word, CAN timeout/freshness, Panda latch denial, untrusted replay clock, EPS temporary/permanent faults, button/driver override, brake and accelerator, disengagement, spontaneous service restart, unexpected Galaxy access while onroad, disabled/absent modem, limited battery/thermal, modeld stalls, camera starvation, crash/restart, and OTA rollback. Assert that optional services never grant engagement and no safety output is sent in default OFF.

For any longitudinal proposal, explicitly validate stock ACC behavior, FCW/CMBS/AEB state, ownership of radar/ADAS ECUs, stop/start priority and lack of unintended UDS/CAN transmission. Do not infer these from the previous Dom engagement failure.

## 11. Decision log and sequencing

1. **APPROVED AS STRATEGY:** MVL-first for the Accord 11G; stock Honda/Bosch-C controller is the final authority.
2. **APPROVED AS CANDIDATE ONLY:** MVL-native StarPilot visual adapters and local Galaxy read-only service.
3. **CONDITIONAL/BENCH ONLY:** StarPort, Bluetooth, Soloist, companions, model downloads, sentry, power actions.
4. **OFFLINE ONLY:** AOL, lane centering, FLM/torque, SLC automatic cruise writes, curve active speed, Conditional mode and longitudinal profiles.
5. **EXCLUDED:** Brand-specific vehicle adapters for non-Honda makes; Dom Honda control/Panda replacement; physical CAN transmission during assessment.
6. **BLOCKED:** Claiming an independent review PASS, AGNOS/Panda build success or comma deployment readiness based on this assessment.

## 12. Reproducible evidence index

- INVENTORY_COVERAGE.md — inventory reconciliation methodology and counts.
- dom_full_file_disposition.csv — every one of 9,269 Dom entries; path SHA, MVL match, disposition, source evidence.
- mvl_only_files.csv — all MVL-only paths.
- dom_module_inventory.csv — 684 module/folder buckets.
- feature_family_review.csv — all 32 feature families and explicit decisions.
- source_component_review.csv — 983 first-party code components with source/Symbol evidence.
- runtime_starport_references.csv — cross-namespace StarPilot mentions.
- parameter_key_references.csv — Dom literal settings references.
- shared_parameter_literal_keys.csv — 254 overlapping Dom/MVL literal names, with source owners.
- protected_runtime_differences.csv — protected/risky changed paths.
- honda_controller_crosswalk.csv — 16 Dom-to-MVL Honda source files.
- syntax_parse_errors.csv and static_validation_summary.json — actual Python parse results.
- manifest_summary.json and feature_catalog_summary.json — machine-readable reconciliations.
- scan_dom_mvl.py, validate_sources.py and feature_catalog.py — offline reproducibility scripts.

## 13. Final technical verdict

The pinned repositories have been comprehensively inventoried at **file level**, all first-party subsystem families dispositioned, all inspected first-party source components indexed, and core Honda source conflicts confirmed. This supplies a defensible engineering basis to start **non-driving, isolated MVL adapters**.

The request for a *fully independently reviewed, build-tested, and on-device validated end-to-end assessment* is **not yet fulfilled**. The independent agent runners did not complete, Ubuntu is offline, and native/Panda/hardware evidence is absent. The assessment must not be described as an installation-ready or safety-qualified migration. The next warranted deliverable is a small MVL-native read-only adapter with independent review and tests, not a wholesale feature import.
