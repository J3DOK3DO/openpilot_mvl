# G10 isolated AGNOS 19.8.1 AArch64 build environment

Status: SCons graph preflight PASS; representative native binary build in progress. Full cold product build HOLD until Qualcomm model compilation prerequisites are available. No device installation or reference-image modification.

## Pinned inputs and source boundary

- PR #1 parent: `b070247da792f216a558e250078caf62d201d97e`; isolated branch: `codex/mvl-g10-continuation`. Record `git rev-parse HEAD` before each build.
- AGNOS reference: `/home/jdkd/AGNOS_20261014/agnos_system.ext4.img`, SHA-256 `98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8`, `/VERSION` = `19.8.1`. Use a separate extracted copy under `/mnt/commadrive/MVL_G10_AGNOS_19_8_1_ROOTFS`; never write the image.
- ARM64 execution image: `starpilot-larch64-builder:latest` at local image ID `sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95`. Disable the network and mount the extracted AGNOS root read-only.
- The extracted AGNOS tree has its own AArch64 `/usr/local/venv/bin/python3`, SCons, capnpc 1.0.1 and pinned comma dependency packages. Its Python is 3.12.3 and Clang is Ubuntu 18.1.3. A separate audited ARM64 site-packages tree imported successfully but is unnecessary for the supported AGNOS build.
- Six submodule Git link SHAs match the preserved audit source. Copy their contents into the isolated worktree before building because Panda SConscript writes generated files into its own directory. Do not modify the audit source. The submodules are `msgq_repo`, `opendbc_repo`, `panda`, `rednose_repo`, `teleoprtc_repo`, `tinygrad_repo`.
- LFS ONNX files in the PR checkout are pointers. The preserved audit copies match both pointer sizes and SHA-256 values. Do not claim a full cold build while model inputs or a Qualcomm GPU/compiler runtime are absent.

## Supported architecture selection

`SConstruct` selects `comma_arm64` only when `uname -m` is `aarch64` and `/AGNOS` exists. The actual AGNOS userspace chroot satisfies both. It chooses Clang/Clang++, `-D__COMMA_HARDWARE__`, `-mcpu=cortex-a57`, target AArch64 system libraries and a separately supplied `cache_dir`. A generic ARM64 container without `/AGNOS` selects the PC `aarch64` path and cannot certify the comma build.

## Reproduction on this host

Check image and free space first, then run the following from the isolated source worktree. The source mount is writable only to capture generated objects; the AGNOS copy is read-only. Use `--mount` so a missing path fails instead of being silently created. The original ext4 image is never mounted writable.

```sh
docker image inspect --format '{{.Id}} {{.Architecture}}' starpilot-larch64-builder:latest
sha256sum /home/jdkd/AGNOS_20261014/agnos_system.ext4.img
df -h / /mnt/commadrive
docker run --rm --platform linux/arm64 --network none --read-only \
  --tmpfs /tmp:rw,size=512m \
  --mount type=bind,src=/mnt/commadrive/MVL_G10_AGNOS_19_8_1_ROOTFS,dst=/agnos,readonly \
  --mount type=bind,src=/dev,dst=/agnos/dev,readonly \
  --mount type=bind,src="$PWD",dst=/agnos/src \
  --mount type=bind,src=/mnt/commadrive/MVL_G10_BUILD_CACHE,dst=/agnos/build_cache \
  starpilot-larch64-builder:latest \
  sh -c 'chroot /agnos /usr/bin/env PATH=/usr/local/venv/bin:/usr/bin:/bin HOME=/tmp /bin/sh -c "cd /src && /usr/local/venv/bin/python3 -m SCons -j4 --minimal cache_dir=/build_cache openpilot/common/libparams_c.so"'
```

For graph preflight, replace the final SCons target with `-n --minimal cache_dir=/build_cache`; this completed with exit 0 and included the full minimal product graph. Do not interpret a dry-run as built binaries. An earlier attempt using `PATH=/usr/bin:/bin` failed at `capnpc: command not found`; the AGNOS venv PATH above resolves it. The model SConscript selects `DEV=QCOM` plus device-specific warp and ONNX compilation. This host lacks a Qualcomm GPU, so a full product build is not yet prerequisite-qualified. `SKIP_TINYGRAD_COMPILE=1` is a source-supported partial build switch, but it does not yield a full cold product build and is not used to promote TARGET_BUILD_READY.
