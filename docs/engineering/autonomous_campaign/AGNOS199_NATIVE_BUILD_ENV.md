# AGNOS 19.9 isolated native build environment

**Scope:** host-only AArch64 toolchain readiness for frozen product source `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`. No comma operation or product qualification.

## Reproduction pins

- Verified raw system ext4 SHA-256: `80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7`; `/VERSION=19.9`. See `AGNOS199_IMAGE_PROVENANCE.json`.
- Extracted rootfs: `/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs`; original downloaded xz and reconstructed raw image remain separate.
- Frozen source worktree: `/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263`; seven submodule gitlinks materialized at their pinned SHAs; source preflight PASS with no dirty paths before the native build. Build outputs in this worktree are disposable; the tracked source commit remains frozen.
- Network-disabled AArch64 runner image ID: `sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95` (`starpilot-larch64-builder:latest`, locally pinned by ID check). The rootfs is mounted separately; runner image is only an emulation/container envelope.
- Reproduction wrapper: `tools/release/agnos199_native_probe.sh graph|lib`; it checks rootfs version, image SHA, source SHA and runner image ID, sets `--network none`, and runs inside the extracted 19.9 rootfs. Its host-specific Git object bind paths are intentional and must be reviewed if moved.

`SConstruct` reads `uname -m=aarch64` and `/AGNOS` inside the chroot and selects `comma_arm64`, Clang/Clang++, `-mcpu=cortex-a57`, and `/usr/lib/aarch64-linux-gnu`. The model recipe then selects `DEV=QCOM`; the graph dry run creates no model artifacts. The isolated cache path is `/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/build_cache`, not the installed device cache.

## Native tools observed in the verified rootfs

| Tool | Result |
| --- | --- |
| Python | `/usr/local/venv/bin/python3` 3.12.3, executed in chroot |
| SCons | Python module 4.10.1 imported; full source graph dry run completed |
| capnp / capnpc | Python module 2.1.0 imported; `capnpc --version` 1.0.1; schema generation reached during library build |
| NumPy / Cython | 2.5.1 / 3.2.9 imported |
| Clang | 18.1.3; compiled a toy AArch64 ELF relocatable object, SHA-256 `ba44c8cb56a8eb97d5ba06b913f97cfdc264ffb2e88e5b60cb2abdcadf2d7bc4` |
| readelf | GNU Binutils 2.42; toy object reported AArch64 ELF64 |
| Git | available in rootfs when `/dev` and required read-only Git object paths are bound |

The current image's SCons version differs from the `uv.lock` pin 4.11.1; the actual 19.9 image has 4.10.1. Its successful graph evaluation establishes this bounded use only. No arbitrary package install occurred. Exact selected executable and library hashes are in `AGNOS199_DEPENDENCY_INVENTORY.json`.

## Build results and limits

`graph` completed `scons: done building targets` from frozen 4b source, using AGNOS 19.9. Log: `/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/agnos199_scons_graph.log`. The one-library log reaches `scons: done building targets` after linking `libparams_c.so`; the 3,484,104-byte ELF64 AArch64 output has SHA-256 `2594c615b0c97bd610ccc32606077d3fef9b8dc1e273662df9df28ee3ce0da8c`. Result: **PASS_NATIVE_BINARY_BUILT_WITH_LOG**. The subprocess exit code and 19.9 runtime load were not captured. Full ELF dependencies and RUNPATH are recorded in `AGNOS199_BUILD_TEST_RESULTS.json`. The image remains unmodified; host extraction and compilation use separate paths. A graph PASS or representative ELF is not six QCOM captures, a full cold product, target boot, or device qualification. Full product compilation remains gated by exact-source QCOM artifacts and measured capacity.
