# AGNOS 19.9 model-independent native build

Target: `openpilot/cereal/libsocketmaster.a`, from `openpilot/cereal/messaging/socketmaster.cc` and generated `services.h`. The exact command is in `CAMPAIGN6_SOCKETMASTER_BUILD_20261108.sh`; log is in the adjacent `.log`. Frozen source commit: `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`. Rootfs version: 19.9; image SHA-256: `80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7`. Builder image ID equality was checked against `sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95` before execution.

Container: network none; source and rootfs bind-mounted read-only; dedicated writable `/agnos/build_cache`; read-only container layer; 1 GiB RAM, one CPU, 64 processes, 300-second timeout, no new privileges, user 1000:1000 in chroot. `clang++` 18.1.3, `-std=c++1z -D__COMMA_HARDWARE__ -mcpu=cortex-a57` and SConstruct warning/optimization flags. The first two attempts failed before successful compilation due absent output mountpoint and capnproto include path; both were corrected in the saved script. Final exit 0.

`socketmaster.o`: ELF64 little-endian AArch64 relocatable, 965744 bytes, SHA-256 `ab078b66bc94231b57a8fc13d7b942dd6f1ba68fa64d51a7ee4c64f6aaebc423`. Archive: one `socketmaster.o` member, 972156 bytes, SHA-256 `05c251e4214dfd2600f489dfdd7f21f2058e8aee794c0607844caeb7f8655d6a`. `SubMaster` symbols present. Relocatable objects have no `DT_NEEDED`, RUNPATH or RPATH; final link dependencies and target runtime remain unverified. This is not an SCons build or full product.

Panda diagnostic: SCons traverses `panda/SConscript` for unrelated targets, and its Git version calls rejected host-owned `/src/panda`; staged version became `DEV-unknown-DEBUG`. The msgq target graph and archive built, but Panda version provenance was degraded. A process-scoped `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/src/panda` returned `8a16e089`, matching the pinned Panda gitlink. No global configuration or Panda source changed. A full SCons rerun using this fix remains unexecuted.

B3 remains deferred by owner (0/6), so full G10 product remains NOT_BUILT.
