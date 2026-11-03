# G10 — ARM64 / AGNOS qualification preparation

**Campaign:** 2025 US Honda Accord 11G Hybrid Bosch-C/CAN-FD, MVL-first StarPilot integration. **Source baseline:** M0–M3 commit `f19b4ea0dfd0f3e3ab2537dba2d0bfb863760ed0`, upstream `376c44b5731b2655e5c2f301b73c9729eb499e91`.

## Actual read-only evidence

- Inspected offline file `/home/jdkd/AGNOS_20261014/agnos_system.ext4.img` through read-only `debugfs`. Root VERSION reports **19.8.1**; issue reports **Ubuntu 24.04.5 LTS**. This is **not** a running comma-device attestation.
- Recomputed full-image SHA-256 **`98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8`**, matching pinned offline evidence.
- Inspected MVL host `libparams_c.so` and `ipc_pyx.so`; both contain ELF e_machine **62 (x86-64)**, not target ARM64 e_machine 183.
- Ubuntu available `/mnt/commadrive` capacity at probe: **8,148,623,360 bytes** (~7.59 GiB). Full isolated no-cache cold build would risk disk exhaustion; do not delete historical evidence to make it fit without separate review.
- The host PATH lacks both `aarch64-linux-gnu-gcc` and `aarch64-linux-gnu-g++`. Clang, qemu-aarch64-static, readelf and debugfs exist, but these alone are **not** proof of a complete matching AGNOS toolchain or ABI.
- The exact source checkout for the native host samples is MVL commit `376c44b5731b2655e5c2f301b73c9729eb499e91`.

The script `agnos_passive_check.py` produces `G10_AGNOS_PASSIVE_EVIDENCE.json` without privileged mounting, changing the ext4 image, or communicating with a car. The companion unit suite `test_agnos_passive_check.py` passed **9/9** cases. The command allowlist explicitly rejects debugfs write mode and unknown mutating shell commands. This is a **passive preparation PASS**, not a G10 target-build PASS.

## Required build and hardware completion sequence

1. Reserve a dedicated external or separate engineering build volume, provision more space than the cold build's measured artifact footprint (15 GiB free as a conservative *planning threshold*, not a sufficient guarantee), and avoid filling the 92%-used existing volume.
2. Build in a separate pinned MVL branch/workspace using exact opendbc, Panda, msgq and AGNOS sysroot identities. Acquire a valid target cross compiler and appropriate Python/C++ dependencies; do not silently copy Dom's nanobind libraries into MVL's Cython IPC.
3. Perform a **full clean AArch64 native compile**, capture compiler provenance, artifact hashes, ELF e_machine=183 for target binaries, interpreter/loader, dependency linkage, RUNPATH and complete dependency-closure records.
4. Validate the exact comma model/AGNOS version on actual hardware and match installed firmware/device identities. Existing file VERSION 19.8.1 alone cannot establish what the device is currently running.
5. Qualify off-vehicle isolated bench startup, process scheduling, UI rendering and GPU/encoder/USB load, thermal/memory budgets, crash/restart and protected rollback. Do **not** assume that compiled code is safe on a vehicle.
6. Separately validate Panda safety policy and the actual Honda stock ACC, FCW, CMBS/AEB, override and fault recovery through appropriate protected physical qualification, not replay or source comments.

## Scope and decision

**G10 preparation: PASS. G10 full ARM64 target qualification: HOLD.** The current no-change, read-only audit is suitable for planning only. No vehicle interaction, flashing, ECU diagnostics, or CAN/UDS transmissions were performed. Do not authorize installation or activation of new driving features based on this campaign.

Reproduce:

```sh
python3 docs/engineering/campaign_20261103/g10/agnos_passive_check.py --output docs/engineering/campaign_20261103/g10/G10_AGNOS_PASSIVE_EVIDENCE.json
cd docs/engineering/campaign_20261103/g10
pytest -q -ra test_agnos_passive_check.py
```
