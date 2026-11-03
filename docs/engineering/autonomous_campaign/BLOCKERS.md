# Blockers and dependencies

Updated 2026-11-03. These are **HOLD** gates, not observed failures of the current host suite.

| Blocker | Remediation attempted or evidence gathered | Dependency to clear |
| --- | --- | --- |
| Parameter migration provenance and semantics | G03 marked caller metadata unattested; 254/254 overlapping keys remain DENY. | Source-attested mapping and separate semantic review. |
| Native UI and IPC behavior | G05 host view model passed; high/critical OEM/MVL alerts suppress optional panels. | Native C3/C4 render and device timing tests. |
| Galaxy live security | G06 authenticated GET-only handler passed host tests; default OFF. | Isolated network/auth transport and device resource security review. |
| Model execution | G08 catalog/hash checks passed host tests; no runner enabled. | Model runner, target compatibility, and AGNOS execution qualification. |
| Vehicle control safety | G09 synthetic reason-only evaluator passed; no CAN/control values emitted. | Physical Panda and Honda OEM stock ACC/FCW/CMBS/AEB validation across faults and modes. |
| Target build and boot | G10 inspected AGNOS 19.8.1 image; host native libraries are x86-64; standard AArch64 compiler tools were absent in the recorded environment. | Toolchain and capacity, full AArch64 cold build, physical device boot. |
| Release and recovery | Consolidated host regression passed; no installable combined branch was authorized. | Exact-commit integrated review and protected rollback exercise. |

Earlier review defects were corrected and retested, as recorded in the [master report](../campaign_20261103/CAMPAIGN_MASTER_REPORT.md). The host suite currently has no failing tests.

G06 preflight at `efdc8b4f0dfcae5c3ddc1ae176bec8a6db5044ea` confirmed no production adapter or registration. See [transport readiness](G06_TRANSPORT_READINESS.md); live transport remains HOLD.

Background host check: standard `aarch64-linux-gnu-gcc` absent from PATH; no cold ARM64 build attempted. Exact AGNOS image hash matched prior evidence. See `BUILD_EVIDENCE.json`.

Native raylib UI startup test at `e65dc8aa9053e53d41fb9a7c2f721b3e819557c6` was BLOCKED during collection by missing `capnp` in system Python. A read-only cached pycapnp retry then hit missing `opendbc`; no UI process started. Do not count the 389 offline host tests as native UI startup evidence.
