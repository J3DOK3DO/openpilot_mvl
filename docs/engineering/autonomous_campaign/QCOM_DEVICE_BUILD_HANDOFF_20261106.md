# Exact-source QCOM continuation handoff — 2026-11-06

**Decision: PRODUCT_BUILD_INCOMPLETE / HOLD.** This is a prepared procedure, not authorization to copy, compile, install or activate software on a comma. Read-only SSH preflight returned `NO_ROUTE_TO_HOST`; no device model, AGNOS, GPU, installed branch/SHA, capacity or thermal fact was obtained. See `COMMA4_READONLY_PREFLIGHT_20261106.json`. The existing known-good installation and AGNOS reference were untouched. The earlier G10 document's recovery-media exercise language is superseded by the owner's C4-12 waiver for this restricted profile.

## Trusted inputs and boundaries

- Published parent: `1a878ddec225f92fbbaa74f512fcdbdab7a3ad7c`; exact source-only handoff: `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` at `/mnt/commadrive/MVL_QCOM_HANDOFF_4b25263_20261105`.
- Externally anchored manifest SHA256: `998b417374930b75338b7ef8be9b3739d3e9e4d130c39ae0aa10e4abfcab9ee4`; archive SHA256: `37a82b744d079c0a130b3f88e24ba4d56b7aa5db4c0bc709449ed4f0ba3d60fe`; 4,372 members. Verify both hashes independently before using the handoff verifier. Do not substitute a same-format package with a self-consistent manifest.
- Tinygrad Git link: `92b742f711c7d216fd3ed7a46a30a959e3c43bd4`; AGNOS 19.8.1 reference image SHA256: `98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8`. Preserve original references.
- Previous exact-source evidence: 444 host tests, 13 handoff/recovery units, eight IPC paths, 254 Params keys DENY, 7/7 pinned submodules, 283/283 selected LFS. These were accepted at `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` and were not rerun because model/product source inputs did not change. Current continuation source `c5c2cb367a451dd8f6476e3bd365649938ba16e4` adds only offline observers and their twelve passing focused tests; independent exact-commit source-boundary review passed for this limited scope.
- No stock QCOM output, full cold product, installable package, binary ABI inventory or device qualification exists. CPU/LLVM captures and Dom artifacts are incompatible. `SKIP_TINYGRAD_COMPILE` must be unset.

## Phase A — read-only device preflight (no device writes)

Run `timeout 20s python3 tools/release/readonly_comma4_preflight.py --host comma --timeout-seconds 12` from the reviewed host checkout. The tool uses BatchMode SSH, strict host key checking and a fixed read-only shell probe. Capture JSON and exit status. Require observed AArch64, AGNOS 19.8.1, `/AGNOS`, Qualcomm GPU character device, compiler paths, available storage/RAM, thermal readings, and installed known-good branch/SHA. The tool's 12 GiB `/data`, 2 GiB `/tmp`, 2 GiB `MemAvailable`, and 70 °C planning thresholds are conservative stop criteria, not device safety certification. Owner must independently confirm the known-good branch/SHA. `NO_ROUTE_TO_HOST`, any missing value, or contradictory observation is HOLD. Never infer permission from a successful probe.

## Phase B — separately authorized QCOM compilation only

Before any source copy or compilation, obtain separate authorization for that device-side action. Use a parked, vehicle-disconnected comma on stable power, with owner-managed recovery reference. Create an empty isolated path such as `/data/mvl-builds/4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb/source`; never build in `/data/openpilot` or alter the known-good installation. Copy the verified handoff only after authorization, preserve its manifest/archive identity, and verify exact source HEAD, seven pinned gitlinks, all 283 selected LFS bytes, two ONNX identities, AGNOS and tinygrad compiler. Stop if available disk, memory or thermal headroom falls below the preflight guardrails. Limit parallel jobs to four or lower according to measured headroom.

`openpilot/selfdrive/modeld/SConscript` selects `DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1` on `comma_arm64`. It must produce exactly:

1. `dmonitoring_model_tinygrad.pkl`
2. `driving_tinygrad.pkl`
3. `driving_warp_1344x760_tinygrad.pkl`
4. `driving_warp_1928x1208_tinygrad.pkl`
5. `dm_warp_1344x760_tinygrad.pkl`
6. `dm_warp_1928x1208_tinygrad.pkl`

After the prerequisites above pass, run the documented SCons six-target command from `G10_FINAL_BUILD_CLOSURE_20261105.md` with a fresh isolated cache, `-j4` maximum, an operator-set finite timeout, and external sampling of disk, memory and thermal state. Capture exact command, environment allowlist, UTC start/end, exit code, stdout/stderr, source SHA, compiler gitlink, target model/AGNOS and GPU identity. Stop on OOM, GPU fault, thermal alarm, storage decline or source mismatch. Do not reuse CPU/LLVM or Dom captures and do not install an output from this phase.

Copy only six outputs into a new private evidence directory. Run `python3 tools/release/mvl_model_artifacts.py record` and `verify` with `--source`, `--onnx-assets`, `--artifacts`, `--agnos-image`, `--agnos-root`, and `--manifest` as specified in `G10_MODEL_ARTIFACT_PREFLIGHT.md`. Preserve each artifact SHA256/size and the manifest SHA256. The validator statically scans capture structure and source/ONNX/AGNOS provenance; it does not execute inference or make the target build qualified.

## Phase C — full product, only after six-output verification

Use a separate isolated staging checkout, clean cache and supported native AGNOS 19.8.1 toolchain for a full cold SCons product build. Do not run the destructive stock release script against an installed tree. Record build command, source commit, builder image digest, target architecture, compiler version, environment flags, process exit status and complete logs. Run static QCOM `verify` first, then bounded `timeout 300s python3 tools/release/inspect_native_product.py --source-root <exact-source> --staging-root <separate-product-stage> --qcom-manifest <manifest.json> --expected-source 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb > <private-inventory.json>`. The inspector hashes staged files and records ELF class, AArch64 machine, OS/ABI, interpreter, NEEDED, RUNPATH/RPATH and build ID. Review every dependency against the pinned AGNOS rootfs, package metadata, six model bytes and SCons build log. A static inventory PASS alone does not prove a complete build, load, inference or device boot.

After any changed product-source checkpoint, rerun the required combined regressions and independent exact-commit review. Keep C4-01–07 and C4-09–11 NOT_TESTED until an authorized install and actual bench evidence. C4-08 remains excluded while G06 is unregistered. C4-12 is `WAIVED_BY_OWNER / NOT_EXECUTED`; no restoration exercise is required. Do not activate experimental vehicle control or touch Panda/ECU policies. If the device remains unreachable or compilation is unauthorized, retain `PRODUCT_BUILD_INCOMPLETE` and this complete handoff.
