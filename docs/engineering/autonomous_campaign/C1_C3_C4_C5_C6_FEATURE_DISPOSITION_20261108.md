# Campaign 5 feature disposition

| Feature | Campaign 5 disposition | Remaining proof |
| --- | --- | --- |
| Lane centering / Honda ACC | EXISTING_ACTIVE_CONTROL_UNCHANGED | OEM/Panda evidence remains external; LaneCentering=0 preserved |
| Native status badge / G05 | PARTIAL_HOST_PASS | Hidden HOME no longer reads supplier; 92 host tests pass; production supplier remains OFF; native timing/fallback on Comma 4 pending |
| Honda warning priority | PARTIAL_HOST_PASS | Native C4-05 display proof pending |
| StarPilot bridge and IPC | PARTIAL_HOST_PASS | Host read-only view/bridge tests pass; device IPC pending |
| G08 metadata | PARTIAL_HOST_PASS | Exact loaded runner/model identity on target pending |
| Galaxy G06 | OFF_UNREGISTERED | Separate security and target review before registration; C4-08 conditional N/A |
| StarPort | EXCLUDED_PENDING_CONTRACT | No approved non-actuating source contract found |
| Startup/shutdown/fault | PARTIAL_HOST_PASS | Native cold boot and fault fallback pending |
| Restricted Params | DENY_254 | No new authorization; runtime target review pending |

B3 is DEFERRED / OWNER-ACCEPTED SCOPE EXCLUSION and 0/6; exclusion grants no feature or release PASS.

Fresh frozen-source checks: `openpilot/common/params_keys.h` defines `LaneCentering` default `0`; the G03 evidence JSON has exactly 254 entries, all DENY with read/write false. Campaign 5 does not modify either file.
