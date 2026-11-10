# C19 clean-install display-only Comma 4 candidate

**Release classification:** CLEAN_INSTALL_OFFLINE_CONTRACT_VERIFIED / PHYSICAL_HARDWARE_HOLD.

This is a minimal **disconnected, static status dashboard**, not the original full MVL–StarPilot live-data driving dashboard. It displays no car speed, CAN, steering, camera, cruise, or controls data. It cannot control a car. No steering, brake, longitudinal, Panda/CAN or manager processes are intentionally included in the installed payload.

## Intended target and startup

- Hardware: comma four (MICI); AGNOS 19.9; AArch64.
- Genuine AGNOS setup invokes a downloaded custom installer, which places the application at /data/openpilot and creates /data/continue.sh.
- This branch adds a separate root installer, two minimal launch scripts and displayonly/c19_display.py. The installer downloads only the included checksum-pinned small runtime tar, not the full driving-capable repository.
- The installer must reject non-MICI devices and wrong AGNOS. The launch scripts refuse missing Comma DRM/display access and known driving processes.
- Native Comma Raylib and Python 3.12 packages must actually exist on the device. No on-device graphics test has been performed, and prior QEMU headless full render crashed.

## Distribution and integrity

- Source repository: J3DOK3DO/openpilot_mvl.
- Engineering branch: mvl-c19-displayonly-cleaninstall-20261110.
- Source files: installer, displayonly/c19_display.py, displayonly/launch.sh, and launcher overrides.
- Payload file committed in this branch: displayonly/C19_CLEAN_INSTALL_PAYLOAD.tar.gz.
- The installer hard-codes the exact expected SHA-256. Rebuild using the Python packaging script and verify bit-identical repeated builds, runtime membership and the pinned hash.
- The standard installer.comma.ai/<owner>/<branch> shorthand is for repositories conventionally named openpilot, not openpilot_mvl. A separately verified custom URL serving the root installer is required. A URL is not verified simply because code exists in this branch.
- This branch/publication is not an install authorization.

## Owner-chosen rollback

The owner reports that the exact previous software branch/commit is already recorded; its manual reinstall procedure is already known; and desired settings are saved or intentionally expendable. Do not ask to repeat these steps or copy their values into the repository.

The owner selected **manual reinstall** as the fallback and waived a full physical partition-image backup and restoration rehearsal **for this clean-install option only**. The waiver does not mean those requirements passed, and manual reinstall cannot necessarily recover a corrupted OS, boot partitions, inaccessible device, or erased private data.

## Qualification gate

Offline source/package tests and an independent source review do not demonstrate the physical GPU, power or boot result. The actual device has **not been contacted or modified**. Do not use this release on a car.

Before any physical installation, confirm separately the device identity, supported stable power, isolation from vehicle/Panda/CAN, exact published script/archive hashes, written bounded installation authorization and means to return to the previous software. A display-owner conflict or device model/version mismatch is a STOP.

**INSTALL_ALLOWED=false. ACTUATION_ALLOWED=false. PHYSICAL_GPU_RENDERING=NOT_RUN. RELEASE_STATUS=HOLD.**
