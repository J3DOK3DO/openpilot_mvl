# Accord 11G — MVL-first StarPilot:Dom selective integration

Assessment date: 2026-11-02
Status: planning and source assessment only; not a qualified vehicle release.

## Locked source identities

- Foundation: mvl-boston/openpilot, sp-honda-dev-202608, a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1
- User fork: J3DOK3DO/openpilot_mvl, sp-honda-dev-202608, same SHA.
- Honda opendbc submodule: mvl-boston/opendbc, 3fec9a418a659de31d7b1f494193161697a35071
- Donor: StarPilotHQ/StarPilot, Dom, 9ef9ef54b23218fd06c8f59f6a8cfd6f780770e8.
- Scope: US Honda Accord 2025 Hybrid / HONDA_ACCORD_11G / Honda Accord and Hybrid 2023–26, Bosch-C CAN-FD as defined by MVL. Do not assume related Honda vehicles are identical.

## Main architecture decision

MVL owns car identification, Honda CarInterface, CarState, CarController, opendbc, CAN payloads and frequencies, Panda/firmware safety policy, radar/stock-ACC ownership, MADS and native controller/tuning. StarPilot:Dom is a donor for isolated UI, Galaxy, StarPort, sound, telemetry, and selected offline-only lane/curve algorithms.

Do not merge full StarPilot or wholesale replace MVL submodules. All donor features default off until independently accepted. Maintain a typed compatibility boundary. Retain the original upstream and existing installations unchanged.

## Honda protected paths

- opendbc_repo (entire pinned gitlink); specifically opendbc/car/honda/{values.py,interface.py,carstate.py,carcontroller.py,hondacan.py,fingerprints.py,radar_interface.py,lane_path.py,hud_objects.py}
- panda gitlink and safety/modes/honda.h
- openpilot/sunnypilot/{mads,modeld_v2}/ and steering/torque controller extensions
- openpilot/common/params_keys.h, cereal schema and services.py; no unreviewed cache or Params reuse
- Actual factory ACC, AEB, FCW/CMBS behavior, steering override and driver control

The MVL interface includes an alpha-longitudinal AEB/CMBS warning and radar handover logic. Never infer that factory ACC and AEB necessarily survive a software error or alpha-longitudinal switch. Verify the exact stock-ACC mode separately.

## Porting waves and release gates

### M0 — assessment and guard rails
Pin exact revisions and submodules. Generate path-level diffs, interfaces, dependency closures and license/notice inventory. Create a script rejecting any protected-path change for initial releases. No control code change.

### M1 — integration chassis
Implement an MVL-compatible StarPilot adapter namespace and feature registry with vehicle identity checks, disabled-by-default flags, readable feature status, and compatible offroad settings. Snapshot/restore Params without importing incompatible binary caches or overwriting calibration. Startup with every flag off must reproduce MVL behavior.

### M2 — native visuals and alert-safe sound
Port chosen layout, road overlays, HUD gauges, settings pages, colors, fonts, optional sound packs and localized text. Preserve MVL renderer/driver monitoring/alert priorities. Reject misleading stale overlays. Test both screen formats and resource utilization; no changes to CAN or control outputs.

### M3 — Galaxy local read-only
Port authenticated local Galaxy web shell, read-only system monitor, logs, trips, route summaries and safe API adapters. Initially off and loopback bound. Never directly expose Params, shell, active logs, or unsafe updater/vehicle mutation endpoints. Threat-model auth/session/path traversal, privacy, bounded processing, and network exposure; then separately consider native launcher and whitelisted settings.

### M4 — offline lateral research
Evaluate Dom lane-centering contribution, lane change smoothing, turn assist, torque shaping and learning against MVL MADS, NNLC and latcontrol_torque extensions. The documented Dom lane-centering live admission is tagged Ioniq 6, not Honda. No Honda admission/live steering. Compare deterministic control traces, freshness, override, frame gaps, hard bounds and existing native limiter. Keep only improvements demonstrated in new exact-baseline evidence.

### M5 — StarPort and speed advisory
Isolate StarPort Bluetooth, Wi-Fi/USB, signed package identity, GPU renderer, encoder and Galaxy setup service. Begin with desktop DHU/harness, then physically disconnected/benched hardware tests. Do not share production control processes or interfere with driver monitoring. Speed-limit and curve-speed proposals are read-only telemetry/UI; no automatic Honda SET/CAN actions.

### M6 — optional services
Selectively port model catalog UI, Bluetooth, maps, navigation, sound, Sentry and status-only software update UI after dependency/license/ABI/security review. Keep one owner per service and disabled-first behavior. Automated updater and paired inference require separate capability and recovery proof.

### M7 — separately gated control proposals
Do not activate StarPilot AOL, lane-centering, learned steering, actual SLC/curve speed or Bosch-C longitudinal control by default. Each needs a dedicated signed-off review, native host/Panda tests, bench integration, device timing, OEM collision-mitigation and driver-override evidence, fail-silent/rollback verification and supervised vehicle tests. Offline test PASS is not vehicle qualification.

## Source inventory summary

openpilot/ common path status: 551 identical SHA, 524 modified, 387 MVL-only and 3,279 Dom-only paths. Source file counts: MVL 1,462; Dom 4,354.
opendbc path status: 221 identical SHA, 209 modified, 95 MVL-only and 822 Dom-only. File counts: MVL 525; Dom 1,252.
These are blob/path differences, not validated behavioral changes.

## Decision and release policy

- GO: UI/dash features, alert-safe sound pilot, read-only Galaxy, offline lateral research, isolated StarPort engineering.
- CONDITIONAL: Galaxy settings mutation, model management, system update and actual projection after security and platform evidence.
- NO-GO now: Dom carcontroller, Panda or opendbc overwrite; direct live Dom lane control on Accord; alpha-long assumptions; automatic factory fallback claims; unqualified active speed control.
- Preserve baseline source, license notices, exact source SHAs and rollback artifacts.
- Each feature PR must include upstream path, adapter, tests, source-bound proof, failure modes and compatibility disposition.
- No device flashes, CAN transmissions, vehicle actuation, or road tests were authorized by completion of this planning artifact alone.

Full 84-item machine-readable inventory is provided separately as Accord11G_MVL_First_Feature_Matrix_20261102.csv and 5-sheet integration workbook.
