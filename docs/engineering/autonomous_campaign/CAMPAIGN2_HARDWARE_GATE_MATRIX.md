# Campaign 2A hardware gate — 2026-11-07

**Decision: B2_HARDWARE_NOT_QUALIFIED.** Read-only inspection is permitted; device staging, compilation, and installation remain unauthorized. The actual comma mici is AArch64/AGNOS 19.9 and its installed `sp-honda-dev-202608` HEAD was observed as `a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1`. No device files were written.

| Requirement | Actual result | Safety effect and next proof |
| --- | --- | --- |
| Exact hardware and known-good identity | PASS, read-only | Recheck immediately before any future approved action. |
| /data ext4 identity | PASS from mountinfo | The generic `stat -f` text is not the filesystem feature proof. |
| ext4 project quota capability | **FAIL** | `tune2fs -l /dev/sda12` showed neither `project` nor `quota`; /data mount has no `prjquota`/`pquota`. Do not alter features or mounts. An independently proven bounded filesystem or qualified external Qualcomm host would be needed. |
| Hard aggregate storage bound | UNKNOWN | Must enforce all source, Git, cache, HOME, TMPDIR, output and log writes, with ≥2 GiB /data reserve, in an authorized isolated test. `du`, `df`, RLIMIT_FSIZE and cache size alone are insufficient. |
| RAM and GPU containment | cgroup v2 memory controller PASS; workload and GPU bounds UNKNOWN | Test actual memory.max/OOM and driver allocation behavior separately. |
| CPU/GPU thermal observation | Sensor paths PASS; active response UNKNOWN | Validate continuous readings and abort thresholds under an authorized isolated workload. |
| Parked, stationary, disengaged state | UNKNOWN | Five-second passive subscription had 51 pandaStates updates but zero carState/controlsState updates. Establish 30 seconds of fresh concurrent telemetry or a separately verified physically disconnected bench arrangement. |
| Independent abort and safe cleanup | Host fixture tested; device UNKNOWN | Prove device-specific independent monitor, process ownership, termination and cleanup before any build. |
| Six QCOM outputs / native product | 0/6; NOT_BUILT | Device or qualified external QCOM build and later complete product build are separately gated. |

The row-level machine-readable decisions are in `CAMPAIGN2_HARDWARE_GATE_RESULTS.json`; the observations are in `CAMPAIGN2_DEVICE_READONLY_OBSERVATIONS.json` and `CAMPAIGN2_PASSIVE_TELEMETRY_OBSERVATION.json`. Any later device-writing pilot requires all safeguards plus explicit owner authorization. No hardware PASS follows from the host simulations.
