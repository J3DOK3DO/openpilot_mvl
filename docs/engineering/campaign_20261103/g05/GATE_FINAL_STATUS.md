# G05 — Final scoped engineering evidence

**Source base:** MVL M0–M3 commit `f19b4ea0dfd0f3e3ab2537dba2d0bfb863760ed0`; source upstream `376c44b5731b2655e5c2f301b73c9729eb499e91`.

**Workstream:** StarPilot-inspired MVL status presentation models.

**Acceptance:** HOST_PRESENTATION_MODEL_PASS; NATIVE_RENDERER_AND_DEVICE_HOLD.

**Offline host unit tests:** **13 passed, 0 failed, 0 skipped**; raw `FINAL_HOST_TESTS.log`. All output is source/host engineering only.

**Source-backed review findings and remediation:** High/critical MVL/OEM alerts now defer all optional StarPilot panels; native raylib/C3/C4 UI remains unconnected.

**Separation:** New source files only under this gate's dedicated `openpilot/sunnypilot/starpilot_*` package and corresponding `docs/engineering/campaign_20261103/g05/`. No pre-existing controller, Panda, opendbc, manager, carState, ECU diagnostics, sendcan/UDS, or production startup component is altered. No vehicle release permission is granted.

**Open hard gates:** Exact AGNOS ARM64 build, real device UI/IPC/service timing, firmware and Panda safety identity, OEM stock ACC/FCW/CMBS/AEB qualification and final integrated rollback before any car installation or driving feature activation. Synthetic tests cannot replace these requirements.

**Reviewer evidence:** Independent Codex source findings retained where completed; post-fix unit tests and source-boundary verification required before integration. `CODEX_FINAL.md` and source review are advisory, not an OEM or physical safety signoff.
