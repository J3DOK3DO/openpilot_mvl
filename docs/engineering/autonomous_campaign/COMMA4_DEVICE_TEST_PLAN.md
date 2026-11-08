# Isolated comma 4 bench qualification — NOT_TESTED

Profile: `COMMA4_NON_ACTUATING_MVL`. This is a manual procedure for a later authorized, parked, isolated device session. It is not permission to install or activate this candidate. The full product build is incomplete, so execution remains blocked. Record the exact candidate commit, package SHA256, AGNOS version, device identifier, operator, UTC times, commands, raw logs, PASS/FAIL and waiver evidence in a new device report. Never copy VIN, route, location or account secrets into the campaign.

## Entry and protection

1. Confirm exact source/package hashes and signed or otherwise trusted provenance against the release manifest. Refuse an incomplete package, wrong AGNOS, missing model artifact, or modified control/Panda/ECU boundary.
2. With the device disconnected from the vehicle, record the current known-good branch/SHA and the [official comma factory-reset reference](https://comma.ai/support/flash-your-comma) for owner-managed recovery. The owner controls any future recovery. No restoration demonstration or stress test is required for this release profile.
3. Only after separate user authorization for device installation, install the candidate in an isolated bench environment using the device's supported installation path. Do not connect CAN/Panda to a vehicle, flash firmware, write ECU configuration, or enable experimental control.
4. Run tests with a monotonic timestamped logger and capture process status, resource sampling and UI video. Start from the candidate's default configuration; record every opt-in action. Stop immediately on unexpected vehicle-control publication, security exposure, boot loop, persistent UI failure, thermal shutdown or loss of a viable owner-managed recovery route.

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
| C4-08 | G06 opt-in local transport: unauthorized, malformed, oversized and remote connection attempts. | Excluded while production G06 transport remains OFF and unregistered; if admitted later, require a separate device security plan. | NOT_APPLICABLE_WHILE_G06_UNREGISTERED |
| C4-09 | G08 stock model metadata and artifact identity. | Catalog is read-only; manifest hashes match loaded artifacts; no model switching/download. | NOT_TESTED |
| C4-10 | Resource soak on isolated power: CPU, memory, thermal, disk and power over a documented duration. | No thermal shutdown, starvation, storage exhaustion or process leak; attach raw series. | NOT_TESTED |
| C4-11 | Observe Panda identity and stock-process state passively, disconnected from vehicle. | Record identity and firmware evidence if available; no firmware write or safety-policy change. Observation is not OEM/Panda safety qualification. | NOT_TESTED |
| C4-12 | Physical restoration demonstration. | Owner-approved waiver; no execution or PASS claim. | WAIVED_BY_OWNER / NOT_EXECUTED |

## Supplemental parked observation

`tools/honda11g_health/collect_health.py --device --ack-parked --seconds 5 --output-dir <private-output-dir>` is a bounded subscriber-only observation for an authorized, parked bench. Validate with `python3 -m tools.honda11g_health.validate_report <private-output-dir>/health.json`. It does not establish stock ACC, FCW, CMBS/AEB, braking, Panda safety or release acceptance. Keep private output off the release branch until reviewed and scrubbed.

## Decision

Any missing required entry condition or unexecuted applicable check is `HOLD`/`NOT_TESTED`. C4-12 is excluded from the acceptance denominator as `WAIVED_BY_OWNER / NOT_EXECUTED`; automated rollback and rollback stress testing are `NOT_REQUIRED`. Device tests require real comma 4 evidence. G11/G12 remain `NOT_APPLICABLE_TO_COMMA4_PROFILE` only while no new active control, Panda, ECU or CAN-transmit behavior enters the candidate; this is no safety PASS.

## Bounded execution sheet for an authorized session

All commands below are **prepared only**. The product package does not exist yet, so none may run as a candidate qualification now. Before a session, `export CANDIDATE_ROOT` for the separately authorized isolated install and `export EVIDENCE_DIR` for a private output directory; write the exact source/package hashes and device identifier in the session header. Use `timeout` on each observer, tee raw stdout/stderr into `EVIDENCE_DIR`, and record the command's exit code. Do not run any command if the device is vehicle-connected, moving, enabled for control, or lacking the recorded owner-managed recovery reference.

| Check | Bounded command or manual evidence action | Stop/expected result |
| --- | --- | --- |
| C4-01 | `timeout 10s sh -c 'uname -m; cat /VERSION; git -C "$CANDIDATE_ROOT" rev-parse HEAD; ps -eo pid,comm'` | Exact AArch64/AGNOS/source identity; no process crash loop. Capture startup log separately. |
| C4-02 | Record a 30-second screen video from cold start with the candidate's default settings; capture read-only UI process status using `timeout 10s ps -eo pid,comm`. | Original UI visible and optional MVL panels OFF. Stop on missing OEM warning. |
| C4-03 | After explicit local UI opt-in, record a 30-second video plus `timeout 10s ps -eo pid,comm`. | Native header legible, no unsafe overlap or restart. |
| C4-04 | **BLOCKED: device replay harness required.** The existing `test_starpilot_native_status.py` is a monkeypatched host pytest; it cannot inject timestamps or capture video on a comma 4. Before a device session, implement and independently review a bounded isolated UI replay harness with no control publisher. | Original fallback appears within the documented UI freshness bound in actual device video/timestamps. |
| C4-05 | **BLOCKED: device warning replay harness required.** Host warning-priority tests cannot inject simultaneous OEM/MVL warnings into a device renderer. Prepare reviewed offline replay fixtures and capture the actual display for at most 30 seconds. | OEM/high-critical warning wins on the actual device. No live vehicle signal injection. |
| C4-06 | Run `timeout 15s python3 "$CANDIDATE_ROOT/docs/engineering/autonomous_campaign/probe_g03_host_ipc.py"` as an offline schema sanity check; separately record 30 seconds of device message/render timestamps with the supported read-only logger. | Eight fields decode; reviewer evaluates measured latency and queue growth. Host probe alone is insufficient. |
| C4-07 | In the isolated UI harness only, replay malformed/missing read-only status fixtures and restart the UI process through the supported bench control; bound the observation to 60 seconds. | Original fallback remains usable; stop on boot loop or control-path publication. |
| C4-08 | **BLOCKED: production transport not registered.** `test_local_transport.py` exercises only an ad hoc host Unix socket; it cannot establish device UID policy, remote exposure, or the production process state. After separately reviewed integration, run a bounded device harness against the actual service and network namespace, including unauthorized local and remote attempts. | Default service OFF, actual private socket/UID/token and resource limits hold. Host pytest remains supplemental only. |
| C4-09 | On the isolated host, run `timeout 120s python3 tools/release/mvl_model_artifacts.py verify --source "$SOURCE_ROOT" --onnx-assets "$SOURCE_ROOT/openpilot/selfdrive/modeld/models" --artifacts "$EVIDENCE_DIR/qcom-artifacts" --agnos-image /mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/system-19.9.ext4.img --agnos-root /mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs --agnos-version 19.9 --agnos-component-manifest "$SOURCE_ROOT/openpilot/common/hardware/comma/agnos.json" --manifest "$EVIDENCE_DIR/qcom-manifest.json"`. On the device, inventory every `*tinygrad.pkl` in the candidate model directory, reject any missing or extra name against the six names in the verified host manifest, then hash each of those six files and compare its SHA-256 with the manifest. Record the name list and hashes as evidence. | All six exact-source QCOM outputs match and actual candidate files have the same bytes; no model selection or download. Static validation alone is not inference qualification. |
| C4-10 | `timeout 900s sh -c 'while :; do date -u +%FT%TZ; cat /proc/loadavg; cat /proc/meminfo | head -5; df -B1 /data; sleep 5; done'` in the isolated session, with separate temperature/power telemetry from supported device tooling. | No thermal, memory, disk or process fault; retain series and explicit thresholds. |
| C4-11 | `timeout 15s python3 "$CANDIDATE_ROOT/tools/honda11g_health/collect_health.py" --device --ack-parked --seconds 5 --output-dir "$EVIDENCE_DIR/passive-health"` only when the operator has confirmed parked and disconnected bench conditions. | Supplemental allowlisted observation only; no firmware query or OEM safety PASS. |
| C4-12 | No command. Do not execute reset, restoration or rollback stress. Record owner waiver. | WAIVED_BY_OWNER / NOT_EXECUTED; never PASS. |

Items requiring video, fixture replay or supported UI restart need an operator and cannot be reduced to a successful shell exit code. C4-04, C4-05 and C4-08 require new reviewed device harnesses before execution. The command sheet does not authorize installation, activation, vehicle connection, Panda flashing or any ECU/CAN transmission. Applicable checks C4-01 through C4-07 and C4-09 through C4-11 start `NOT_TESTED` and stay so until physical evidence is reviewed. C4-12 remains `WAIVED_BY_OWNER / NOT_EXECUTED`.
