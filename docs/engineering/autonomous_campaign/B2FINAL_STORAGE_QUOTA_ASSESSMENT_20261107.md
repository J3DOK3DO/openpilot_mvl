# B2-Final aggregate storage quota assessment

**Device hard-quota enforcement: NOT_VERIFIED / NO-GO.** The last read-only `/data` free observation was about 8.85 GiB. The exact host source checkout occupied about 1009 MiB; archive plus selected extracted bytes are another 422.0 MiB if kept simultaneously. A proposed 512 MiB pilot quota cannot hold even the measured checkout before compiler scratch, cache, output or logs. It must not be increased merely to claim readiness.

| Mechanism | Aggregate bound? | Prerequisite and limit | Current verdict |
| --- | --- | --- | --- |
| `/data` ext4 project quota | Potentially, per project ID | Verify actual `/data` filesystem, project-quota feature and mount option; allocate distinct project ID; inherit across all run paths; demonstrate ENOSPC at limit and no writes outside project | NOT_VERIFIED_ON_DEVICE |
| `/data` XFS project quota | Potentially | Only if actual `/data` is XFS and project quotas active; prove path assignment and hard limit | NOT_VERIFIED_ON_DEVICE |
| Bounded loopback filesystem image | Potentially limits files inside mounted image | Device mount privilege and image filesystem support; preallocate image while preserving reserve; prove all writes including cache/TMPDIR/logs stay inside and no bind escape | NOT_VERIFIED_ON_DEVICE |
| cgroup v2 memory/CPU/pids | No disk-byte quota | Useful for RAM/process containment, not aggregate storage | NOT_A_DISK_QUOTA |
| `ulimit -f`, `du`, sampled `df`, SCons cache pruning | No aggregate hard bound | Per-file or after-the-fact observations only | REJECTED_AS_QUOTA |

The AGNOS 19.9 rootfs contains `mkfs.ext4`, `tune2fs`, `xfs_quota`, `losetup` and `mount` binaries. Their presence does not establish the actual `/data` filesystem, mount options, privileges or successful quota enforcement. No quota setup or mount was attempted on the comma.

`tools/release/qcom_b2final.py` exposes a host-testable quota decision that never asserts device qualification. `tools/release/qcom_capacity_budget.py` generates six scenarios and keeps `REQUIRED_CAPACITY_UNKNOWN` even when arithmetic fits, because actual Qualcomm peak scratch and output allocation are unmeasured. The scenario JSON is in `QCOM_CAPACITY_SCENARIOS_20261107.json`. A future preflight must prove a true aggregate hard limit for the entire run, measure the source and trial compiler working set, and retain at least 2 GiB free `/data` (4 GiB preferred) through allocation spikes. Until then, staging and compilation are NO-GO.
