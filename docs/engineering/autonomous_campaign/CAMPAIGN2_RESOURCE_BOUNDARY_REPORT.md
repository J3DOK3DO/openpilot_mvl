# Campaign 2A resource boundaries

| Boundary | Observed or tested | Qualification |
| --- | --- | --- |
| /data capacity | 9,284,160 KiB free at read-only snapshot; actual compile peak unknown | HOLD |
| Host disk | Approximately 14 GiB free in /tmp and 24 GiB at /mnt/commadrive during preparation | Host preparation only |
| Device process RAM | 2,421,660 KiB MemAvailable snapshot; cgroup v2 `memory` controller present. Prior short user-scope `MemoryMax=805306368` reflected in `memory.max`. | Actual compiler/OOM protection NOT_TESTED |
| GPU memory | KGSL node observed; allocation accounting and GPU driver failure response unknown | HOLD |
| Thermal | CPU/GPU sensor paths and idle readings observed; sustained load and abort thresholds untested | HOLD |
| Process count/CPU affinity | Planned `-j1`, CPUs 0–7 and finite timeout | Device enforcement NOT_TESTED |
| Storage | Current ext4 project quota prerequisites absent; no hard aggregate limit shown | FAIL/UNKNOWN |
| Watchdog | Host-only process-group fixture passes normal/timeout/heartbeat/disconnect/abort and descendant tests | Device monitor NOT_TESTED |

The host fixture does not sample vehicle state, actual GPU memory, quota consumption, thermal response, or device OOM events. A future pilot requires independent live monitors, hard resource limits where supported, finite timeout, and proven abort before any device write. A host `MemoryMax` setting does not prove Qualcomm GPU containment.
