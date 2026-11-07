# Combined B3/G10 bounded native host proof

Host compiler proof only: no Qualcomm model capture, no complete G10 product, no Comma4 contact, no installation.

An isolated Docker run using the pinned arm64 builder and AGNOS 19.9 toolchain compiled the frozen source common/yuv.cc into an AArch64 ELF64 relocatable object, rebuilt the same object byte-for-byte (SHA256 23d4a8e4a73e79f9f0e6a01138a0de0ef4c757ca42d5704e5b368771c8f9fc68), and linked a 69,888 byte AArch64 ELF64 shared library (SHA256 f586ce5214567159eafa2c35f089ec76210a182525aaf02dee63b2eea372dcd5) requiring libc.so.6.

The first attempt failed closed due to isolated output directory permissions. Subsequent attempts succeeded after changing only that disposable directory. Exact frozen source and AGNOS image hashes were rechecked; frozen source stayed Git-clean. Execution was no-network, container root read-only, AGNOS and source read-only, 1 GiB RAM, one CPU, 64 PIDs, two 64 MiB tmpfs mounts, 16 MiB per-output limit, 135-second timeout, no privileged device mounts. See JSON for commands, hashes and limitations.

Codex sandbox lacked Docker access but the authorized Ubuntu host had the pinned image and successfully executed it. Ubuntu host DRM renderD128 exists, but native Qualcomm KGSL is absent. QCOM output count remains 0/6, full G10 remains NOT_BUILT, physical Comma4 checks 0/10, and the B2 planning waiver is not safety qualification. Release HOLD.
