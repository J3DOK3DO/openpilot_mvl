# Campaign 2C G10 native product build report

**Full cold product build: NOT_EXECUTED / HOLD.** Frozen product source is `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`; AGNOS 19.9 image SHA-256 is `80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7`. The exact source handoff manifest and archive hashes were rechecked without changing their contents. The existing AGNOS 19.9 AArch64 SCons graph and representative `libparams_c.so` are retained host evidence. Neither is a full product.

The stock `comma_arm64` graph requires six genuine source-matched QCOM captures. None exists (0/6), and the B2 hardware gate is `B2_HARDWARE_NOT_QUALIFIED`. A full cold build cannot pass while those inputs are absent; CPU/LLVM and source-incompatible Dom artifacts are rejected. No full binary inventory, installable package or target boot has been produced.

Once six outputs are separately compiled and independently verified, use a fresh isolated checkout of the frozen source, pinned 19.9 rootfs/toolchain, uncached native build, exact SCons command and captured exit status. Record every binary SHA-256/build ID, ELF machine, interpreter, NEEDED/RUNPATH, versioned and transitive dependencies, source provenance and package members. Run exact-source regressions and separate target runtime checks before promoting S13/S14. Do not modify the AGNOS reference or known-good vehicle installation.
