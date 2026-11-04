# Isolated comma 4 bench qualification — NOT_TESTED

Profile: `COMMA4_NON_ACTUATING_MVL`. This is a manual procedure for a later authorized, parked, isolated device session. It is not permission to install or activate this candidate. The full product build is incomplete, so execution remains blocked. Record the exact candidate commit, package SHA256, AGNOS version, device identifier, operator, UTC times, commands, raw logs, PASS/FAIL and restoration evidence in a new device report. Never copy VIN, route, location or account secrets into the campaign.

## Entry and protection

1. Confirm exact source/package hashes and signed or otherwise trusted provenance against the release manifest. Refuse an incomplete package, wrong AGNOS, missing model artifact, or modified control/Panda/ECU boundary.
2. With the device disconnected from the vehicle, preserve the current known-good installation, user data and recovery image using the approved comma 4 recovery procedure. Verify backup hashes and perform a dry restoration path on separate media. Keep a known-good boot route available.
3. Only after separate user authorization for device installation, install the candidate in an isolated bench environment using the device's supported installation path. Do not connect CAN/Panda to a vehicle, flash firmware, write ECU configuration, or enable experimental control.
4. Run tests with a monotonic timestamped logger and capture process status, resource sampling and UI video. Start from the candidate's default configuration; record every opt-in action. Stop immediately on unexpected vehicle-control publication, security exposure, boot loop, persistent UI failure, thermal shutdown or inability to restore the known-good installation.

## Twelve bench checks

| ID | Check and evidence | Acceptance | Status |
| --- | --- | --- | --- |
| C4-01 | Cold boot and process list; record AGNOS, source/package SHA and startup log. | Stock processes start, no crash loop, exact binaries loaded. | NOT_TESTED |
| C4-02 | Default-OFF view and original UI fallback after normal startup. | Experimental view absent until explicit local opt-in; original UI remains usable. | NOT_TESTED |
| C4-03 | Native MVL header rendering with read-only status supplier enabled. | Correct on-device layout, no text overlap or unsafe occlusion in recorded frames. | NOT_TESTED |
| C4-04 | Disconnect status supplier and inject stale/future timestamps in an isolated test harness. | Data expires on UI monotonic time; original fallback renders without frozen stale status. | NOT_TESTED |
| C4-05 | Replay simultaneous Honda/MVL warning fixtures through supported bench harness. | OEM/safety warning priority remains above MVL decoration; no suppressed warning. | NOT_TESTED |
| C4-06 | Measure message arrival, render latency and dropped samples with monotonic clock. | Every required G03 field decodes; no persistent queue growth or stale display. Record numeric distribution and threshold before PASS. | NOT_TESTED |
| C4-07 | Fault injection: malformed/missing read-only fields and UI process restart. | Fail closed to original UI; no boot loop or control-path side effects. | NOT_TESTED |
| C4-08 | G06 opt-in local transport: unauthorized, malformed, oversized and remote connection attempts. | No unauthorized response or leak; bounded resources; service remains OFF by default. | NOT_TESTED |
| C4-09 | G08 stock model metadata and artifact identity. | Catalog is read-only; manifest hashes match loaded artifacts; no model switching/download. | NOT_TESTED |
| C4-10 | Resource soak on isolated power: CPU, memory, thermal, disk and power over a documented duration. | No thermal shutdown, starvation, storage exhaustion or process leak; attach raw series. | NOT_TESTED |
| C4-11 | Observe Panda identity and stock-process state passively, disconnected from vehicle. | Record identity and firmware evidence if available; no firmware write or safety-policy change. Observation is not OEM/Panda safety qualification. | NOT_TESTED |
| C4-12 | Restore known-good installation and verify boot, process status and hashes. | Restoration succeeds and known-good state matches pretest evidence. | NOT_TESTED |

## Supplemental parked observation

`tools/honda11g_health/collect_health.py --device --ack-parked --seconds 5 --output-dir <private-output-dir>` is a bounded subscriber-only observation for an authorized, parked bench. Validate with `python3 -m tools.honda11g_health.validate_report <private-output-dir>/health.json`. It does not establish stock ACC, FCW, CMBS/AEB, braking, Panda safety or release acceptance. Keep private output off the release branch until reviewed and scrubbed.

## Decision

Any missing entry condition or unexecuted check is `HOLD`/`NOT_TESTED`. Device tests require real comma 4 evidence. G11/G12 remain `NOT_APPLICABLE_TO_COMMA4_PROFILE` only while no new active control, Panda, ECU or CAN-transmit behavior enters the candidate; this is no safety PASS.
