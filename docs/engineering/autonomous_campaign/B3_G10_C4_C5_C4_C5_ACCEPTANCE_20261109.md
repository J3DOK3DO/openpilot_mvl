# C4 / C5 device and recovery acceptance — gated checklist

**Current evidence:** authenticated passive Windows snapshot only, SHA-256 `21f732825d9d61580e44e7c33e67cd9f8f4904884e84e96f284641529f13740d`. Network presence is `DEVICE_CONNECTED_READONLY`. Installed source is `376c44b5731b2655e5c2f301b73c9729eb499e91`, which differs from frozen G10. No device mutation occurred. **Physical acceptance: 0/10.** No row below is credited from SSH reachability or an offroad flag.

| # | Required qualified evidence | State |
|---|---|---|
| 1 | Owner witnessed device physically present, vehicle disconnected or independently verified parked with live ignition and motion monitoring | UNKNOWN |
| 2 | Sustained external power and charging under measured load | FAIL in snapshot for USB/DC/PC online; other sustained supply UNKNOWN |
| 3 | Exact AGNOS, chip, GPU driver, DSP and native ABI inventory | AGNOS/arch PASS; remaining UNKNOWN |
| 4 | Exact isolated staged source, seven submodules, LFS and six native model receipts | NOT STAGED; 0/6 |
| 5 | Enforced aggregate quota, measured cache/scratch/output peak and disk reserve | UNKNOWN |
| 6 | Device-tested memory ceiling, CPU/GPU thermal and GPU fault abort | UNKNOWN |
| 7 | Native product launch, IPC/camera/model/UI behavior without vehicle actuation | NOT TESTED |
| 8 | Verified recovery image and complete offline known-good backup manifest with external trust hash | NOT VERIFIED |
| 9 | Stock ACC retained, fail-silent fallback and Panda safety compatibility under controlled offroad bench | NOT TESTED |
| 10 | Independent physical review and rollback drill, with before/after source and data integrity evidence | NOT TESTED |

## Qualification order and aborts

A qualified operator must establish physical parked/ignition/motion exclusion continuously and independently, then power, GPU/driver identity and thermal telemetry, enforced quota plus measured peaks, memory abort and recovery before any future isolated compilation. Any unknown or lost monitor blocks or aborts. B3 output verification and product linking are separate gates. No test here authorizes moving from a host build to installation.

For a later controlled offroad bench, preserve the functioning installed stock ACC path; verify fail-silent behavior, Panda version/safety agreement and no CAN transmit/ignition/steering/acceleration side effect before a vehicle-facing claim. That bench has not happened. Road operation is outside this campaign.

## Deterministic offline backup and recovery preparation

Use `tools/release/offline_backup_preflight.py --root <isolated-host-backup-root> --manifest <manifest.json> --expected-manifest-sha256 <externally-retained-sha256>` only after a host copy and independently trusted manifest exist. The validator hashes every listed byte, rejects extras, symlinks, protected Params and Panda firmware names, and reports `NOT_INSTALLABLE` even on a complete match. No backup root or external manifest was supplied here, so this check was not represented as a PASS. Preserve an owner-managed recovery image identity, current installed source SHA, backup trust hash and restore rehearsal evidence before a future install decision. No restore, installation, or active `/data/openpilot` change was run or scripted for this campaign.
