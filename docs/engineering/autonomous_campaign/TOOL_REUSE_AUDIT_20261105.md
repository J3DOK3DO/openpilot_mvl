# MVL and Dom release tool audit — 2026-11-05

Independent read-only audit compared the pinned MVL tools and Dom reference. MVL `SConstruct`, `openpilot/selfdrive/modeld/SConscript`, `release_files.py` and `build_release.sh` match the preserved original MVL source.

| Classification | Tool | Decision |
| --- | --- | --- |
| Direct reuse | MVL `preflight_readonly.py`, `release_files.py`, `mvl_model_artifacts.py`, focused `test_runner.py` | Exact source/assets and six-output validator; no release mutation. |
| Isolated wrapper | MVL SCons and release-file inventory; Dom `build_manifest.py` concept | `build_qcom_handoff.py` stages source only and verifies every archive member. Future full build requires isolated target wrapper and ELF/dependency/RUNPATH manifest. |
| Adaptation only | Dom laptop/device builders, CI and diagnostics | Dom uses a different five-output QCOM contract, custom runtime, `COMMA_LAPTOP_CROSS_BUILD` and sysroot path absent from MVL. |
| Incompatible | MVL `build_release.sh`, `build_stripped.sh`, `op.sh`, setup scripts; Dom release scripts | Delete worktrees/staging, rewrite refs, force-push, build Panda firmware, alter host settings or hooks. Do not execute unchanged. |
| Unnecessary | Dom active longitudinal/CAN diagnostics | Outside the non-actuating profile. |

MVL selects `comma_arm64` only when `uname -m` is AArch64 and `/AGNOS` exists. Its modeld recipe requires six `DEV=QCOM` outputs. The current Ubuntu host has no Qualcomm GPU; no full cold build was attempted or claimed. No existing source or device was altered by this audit.
