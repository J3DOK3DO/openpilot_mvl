# Campaign 15 — MVL–StarPilot Comma 4 display-only runtime integration

**Engineering result:** PASS within *isolated offline model-independent scope*. **Install and vehicle release: HOLD**. This report describes genuine MVL layouts and native IPC; it is not permission to replace the installed software, use the vehicle interface, or infer Comma GPU qualification.

## Pinned provenance

- Frozen MVL source: `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`.
- AGNOS: 19.9 frozen root filesystem; native ARM64 builder `sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95`.
- C14 genuine AArch64 `msgq/ipc_pyx.so`, `visionipc/visionipc_pyx.so`, `libparams_c.so`, each with successful native imports.
- C15 fresh x86-64 native builds of the three same targets from a **separate** copy of the same frozen MVL source.
- Existing C13 engineering branch, frozen source and historical C14 binary evidence remain unchanged.

## Proven C15 milestones

1. **Corrected isolated AGNOS build environment.** Bind real `/dev/null` and `/dev/urandom` into a temporary `/dev` filesystem. No mount to Comma, Panda or vehicle. The source-specific SCons invocation rechecked all three AArch64 libraries with exit 0 and without the previous missing-null-device warnings. No full product was built.
2. **Actual private target IPC.** AGNOS Python 3.12 loaded the authentic MVL `msgq.ipc_pyx` extension. A genuine `PubMaster(['deviceState'])` sent a labeled synthetic message to a genuine `SubMaster` in isolated `/dev/shm/msgq_c15_private_ui`; receipt was confirmed, exit 0.
3. **Actual MVL UI `SubMaster` live IPC.** An isolated AGNOS process imported `openpilot.selfdrive.ui.ui_state` and `MiciMainLayout`, with publishers for its 33 expected channel names. No vehicle control message was published. Its genuine UI `SubMaster` received the synthetic `deviceState`, exit 0. **Not a graphics render.**
4. **Host-native model-independent UI build.** With the same source SHA, built genuine x86-64 IPC, VisionIPC and Params through SCons, exit 0. Used cached Python 3.12 developer environment; not the Comma target venv.
5. **Actual MVL desktop graphics.** Xvfb with no TCP listener, Raylib 6 desktop backend and Mesa softpipe produced real compact and large offroad layout PNGs. A 12-frame large-layout run with live private `deviceState` receipt exited 0. No manager, Panda, CAN, car controller, longitudinal service, network request or external process was started by the guarded preview harness. The existing UI font assets were loaded from the frozen source checkout; no font assets are distributed in this handoff.
6. **UI status regressions.** C14 AArch64 source-specific status presentation suite passed 15/15 with test-only inert `SubMaster` fixture. C15 live message tests are *not* the C14 fixture result and are recorded independently. Focused C15 release-evidence tests passed 8/8 before the final broader regression.
7. **Evidence checker.** `tools/release/c15_ui_bench.py` is read-only by default. With explicit `--output`, it writes only one new direct JSON manifest within the C15 evidence directory. A PASS means *host bench + target native IPC*, not AGNOS graphical rendering, physical Comma qualification, G10 completion or installation authorization.

## Unresolved target graphics validation

The genuine ARM64 Raylib 6 **HEADLESS EGL surfaceless** backend began initialization but did not produce a frame before the enforced timeout. A direct `eglGetDisplay` call succeeded but `eglInitialize` did not finish in the emulated environment. Logs retain exit 137 from a bounded forced-stop attempt. Software-rendered x86 screenshots are valid host-UI evidence **only**. Qualcomm/Comma EGL and screen devices are hardware-dependent; no GPU was provided in the Ubuntu ARM64 emulation. This gate cannot be marked passed from host results.

## No installation or actuation

The C15 archive and report are **NON-INSTALLABLE**. The existing Comma installation, Panda firmware, CAN bus, Honda ACC and protected Params were not accessed or changed. C15 host screenshots are saved off device only. C14 C4 physically disconnected device acceptance is still **NOT STARTED**. Before any test on a real Comma, a witnessed physical CAN/Panda isolation, verified rollback image/settings, full native display-only package inspection, independent review and explicit device-specific acceptance are required. Continue with C14-C gate plan; **do not run stock `build_release.sh`, `./build --panda`, or a production manager**.

## Separate vehicle/control requirements

B3 authenticated model outputs remain 0/6, full G10 product NOT BUILT, Option B Honda/stock-ACC HIL and protected-parameter acceptance NOT STARTED. C15 does not waive these gates, approve lateral steering, start modeld, flash firmware or permit a road test.

## Evidence paths

- C15 artifacts and rendered outputs: `/mnt/commadrive/MVL_C15_STANDALONE_UI_BENCH_ARTIFACTS_20261110`.
- Native ARM64 engineering source: `/mnt/commadrive/MVL_C14A_NATIVE_IPC_WORK_20261110`.
- x86-64 host-rendering source: `/mnt/commadrive/MVL_C15_HOST_UI_SOURCE_20261110`.
- AGNOS rootfs: `/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs`.
- C15 release tool: `tools/release/c15_ui_bench.py`; regression: `tools/release/tests/test_c15_ui_bench.py`.
- Native logs: `C15_AGNOS_CLEAN_ENV_REBUILD.log`, `C15_LIVE_PRIVATE_IPC_V3.log`, `C15_ACTUAL_UI_LIVE_IPC.log`.
- UI output: `C15_MVL_COMPACT_FULL_HOST_FRAME.png`, `C15_MVL_LARGE_HOST_12FRAMES.png`, `C15_MVL_LARGE_LOOP.log`, and `C15_RENDERED_IMAGE_QA.json`.

**Disposition:** `HOST_UI_BENCH_PASS_AGNOS_GPU_HARDWARE_HOLD`; device installation is prohibited without the C14-C / R0 evidence.

## Independent C15 advisory and post-review hardening

A local Windows Qwen3-Coder assessment of the first C15 engineering checkpoint emitted the raw verdict \`FAIL_MATERIAL_REPRODUCIBLE_DEFECT\`; the original review is preserved **unaltered** in the C15 independent-review evidence directory. Its allegations are not silently converted to a pass. Direct examination found that the source identities were already pinned to identical MVL commits, output flags already default to false, the evidence directory already requires direct-only output with exclusive creation, and the AGNOS EGL failure already forces target GPU HOLD.

The checker was further hardened to confirm SHA-256 equality for **all 17 Git-tracked MVL font files** across the frozen/ARM64/host source trees, reject symlinked output parent folders, and inspect the exact host preview scripts using Python AST to reject any \`.send()\` service other than the literal \`deviceState\`. Malicious font, path and unexpected \`carControl\` send negative tests were added. These are source-specific offline guards and **not a signature authority or device safety release**. A file-bundle SHA-256 manifest is produced in the local C15 evidence folder; no digital signature is claimed. Any independent reassessment is recorded separately from the original raw FAIL.
