# AGNOS 19.9 ABI comparison

The 19.9 system image is independently hash-verified. The comparator is the retained 19.8.1 extracted rootfs, not a claim that the whole 19.8.1 device or all partitions were inspected. `AGNOS199_DEPENDENCY_INVENTORY.json` gives full SHA-256, ELF class/machine, interpreter, NEEDED, RUNPATH and version symbol sets for each selected path.

| Interface | Finding | Decision |
| --- | --- | --- |
| AArch64 ELF/linker | 19.9 libc and `ld-linux-aarch64.so.1` are byte-identical to selected 19.8.1 files; native Clang produced an AArch64 object in 19.9 | COMPATIBLE_VERIFIED for selected files and toy compilation |
| libc, GLIBC symbols | selected libc SHA and readelf symbol inventory identical | COMPATIBLE_VERIFIED for selected file identity; product-wide symbol coverage NOT_VERIFIED |
| libstdc++, GLIBCXX symbols | selected `libstdc++.so.6.0.33` SHA and symbol inventory identical | COMPATIBLE_VERIFIED for selected file identity |
| LLVM/Clang | selected executable hashes identical; Clang 18.1.3 ran in 19.9 | COMPATIBLE_VERIFIED for bounded compile |
| Cap'n Proto | capnpc 1.0.1 and pycapnp 2.1.0 available; source schema generation reached | COMPATIBLE_VERIFIED for schema tooling; all runtime paths NOT_VERIFIED |
| ZeroMQ/zstd/OpenSSL | selected library files identical between rootfs copies; ELF dependencies recorded | COMPATIBLE_VERIFIED for selected bytes; full runtime NOT_VERIFIED |
| FFmpeg/camera | relevant package paths exist but full camera runtime/dependency graph not executed | NOT_VERIFIED |
| NumPy/Cython extensions | imports pass inside 19.9 chroot; native extension coverage incomplete | VERSION_DIFFERENCE_NO_BREAK_DEMONSTRATED for bounded imports |
| Python/SCons | Python executable identical; actual 19.9 SCons 4.10.1 graph PASS, lockfile records 4.11.1 | VERSION_DIFFERENCE_NO_BREAK_DEMONSTRATED |
| Qualcomm GPU userspace and model compiler | `/dev/kgsl-3d0` observed on device, unavailable on Ubuntu; no QCOM capture or driver-runtime exercise | BLOCKED |
| Native product ELF/RUNPATH | `libparams_c.so` built under 19.9 is ELF64 AArch64; NEEDED: libstdc++, libgcc_s, libc; RUNPATH: `/usr/local/venv/lib/python3.12/site-packages/ffmpeg/install/lib`; no 19.9 runtime load or complete product inventory | PASS_BINARY_METADATA_ONLY / HOLD_RUNTIME |

Matching selected bytes narrows ABI risk but does not prove the 19.9 image is operationally equivalent to 19.8.1. No `INCOMPATIBLE_CONFIRMED` result was observed. No device runtime or physical safety gate is promoted by this matrix.
