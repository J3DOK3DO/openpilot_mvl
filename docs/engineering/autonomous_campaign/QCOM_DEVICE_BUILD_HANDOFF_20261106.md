# Exact-source QCOM continuation handoff — 2026-11-06

**Decision: PRODUCT_BUILD_INCOMPLETE / HOLD.** This is a prepared procedure, not authorization to copy, compile, install or activate software on a comma. The older Ubuntu `NO_ROUTE_TO_HOST` record remains historical. Fresh user-supplied, read-only Windows SSH observations on 2026-11-06 identify a comma mici, AArch64, AGNOS 19.9, a Qualcomm GPU node and the installed known-good branch/SHA; see `AGNOS199_DEVICE_OBSERVATIONS_20261106.json`. Ubuntu SSH must not be retried with its passphrase-protected key. The existing installation and AGNOS reference remain untouched. C4-12 is owner-waived and unexecuted.

## Trusted inputs and boundaries

- Published parent: `1a878ddec225f92fbbaa74f512fcdbdab7a3ad7c`; exact source-only handoff: `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` at `/mnt/commadrive/MVL_QCOM_HANDOFF_4b25263_20261105`.
- Externally anchored manifest SHA256: `998b417374930b75338b7ef8be9b3739d3e9e4d130c39ae0aa10e4abfcab9ee4`; archive SHA256: `37a82b744d079c0a130b3f88e24ba4d56b7aa5db4c0bc709449ed4f0ba3d60fe`; 4,372 members. Verify both hashes independently before using the handoff verifier. Do not substitute a same-format package with a self-consistent manifest.
- The archived `README.md` and historical `G10_FINAL_BUILD_CLOSURE_20261105.md` contain AGNOS 19.8.1 instructions and a `-j4` command. For an observed 19.9 target, the 19.9 compatibility and provenance gates in this document supersede those instructions. Use the explicit conditional `-j1` command below if later authorized; do not modify the archived package or its hashes.
- Tinygrad Git link: `92b742f711c7d216fd3ed7a46a30a959e3c43bd4`; AGNOS 19.8.1 historical reference image SHA256: `98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8`. Preserve original references. The actual device runs 19.9; the 19.8.1 image and current artifact validator cannot certify 19.9 compatibility.
- Previous exact-source evidence: 444 host tests, 13 handoff/recovery units, eight IPC paths, 254 Params keys DENY, 7/7 pinned submodules, 283/283 selected LFS. These were accepted at `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` and were not rerun because model/product source inputs did not change. Current continuation source `c5c2cb367a451dd8f6476e3bd365649938ba16e4` adds only offline observers and their twelve passing focused tests; independent exact-commit source-boundary review passed for this limited scope.
- No stock QCOM output, full cold product, installable package, binary ABI inventory or device qualification exists. CPU/LLVM captures and Dom artifacts are incompatible. `SKIP_TINYGRAD_COMPILE` must be unset.

## Phase A — read-only device preflight (no device writes)

The recorded Windows SSH observations already establish model, architecture, AGNOS 19.9, GPU node and known-good identity. The revised read-only probe accepts `comma mici`, separates CPU/GPU readings from limit zones, checks bounded alternative tool paths, and marks 19.9 `OBSERVED_COMPATIBILITY_PENDING` with `BUILD_TARGET_MISMATCH` against the old 19.8.1 artifact manifest. Its storage result remains `REQUIRED_CAPACITY_UNKNOWN` until tooling, cache, outputs and temporary peaks are budgeted. No Ubuntu SSH is authorized in this campaign. An authorized operator may run the probe through a working read-only transport later and retain JSON/exit status. The 70 °C actual-sensor threshold is a planning stop, not a device rating; unknown actual GPU temperature remains a measurement gap. `/tmp` is only 150 MiB total, so any later build must set `TMPDIR` inside its isolated `/data` folder after verifying space. See `AGNOS199_QCOM_READINESS_20261106.md` for capacity arithmetic and dependency checks.

## Phase B — separately authorized QCOM compilation only

Before any source copy or compilation, obtain separate authorization for that device-side action. Use a parked, vehicle-disconnected comma on stable power, with owner-managed recovery reference. First obtain an exact AGNOS 19.9 image/rootfs identity and matching build dependency inventory, or keep compatibility HOLD. Create an empty isolated path such as `/data/mvl-builds/4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb/source`; never build in `/data/openpilot` or alter the known-good installation. Copy the verified handoff only after authorization, preserve its manifest/archive identity, and verify exact source HEAD, seven pinned gitlinks, all 283 selected LFS bytes, two ONNX identities, AGNOS and tinygrad compiler. The tar alone lacks Git metadata and is not a SCons checkout. Stop if measured free space cannot cover archive, source, tooling, cache, output/temp peaks and reserve; stop on actual CPU/GPU thermal alarm, memory pressure or GPU faults. Begin at one job and raise no higher than four only if measured headroom supports it.

`openpilot/selfdrive/modeld/SConscript` selects `DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1` on `comma_arm64`. It must produce exactly:

1. `dmonitoring_model_tinygrad.pkl`
2. `driving_tinygrad.pkl`
3. `driving_warp_1344x760_tinygrad.pkl`
4. `driving_warp_1928x1208_tinygrad.pkl`
5. `dm_warp_1344x760_tinygrad.pkl`
6. `dm_warp_1928x1208_tinygrad.pkl`

After the prerequisites above pass, run the explicit `-j1` six-target command below with a fresh isolated cache and `TMPDIR`, an operator-set finite timeout, and external sampling of disk, memory and actual thermal state. Capture exact command, environment allowlist, UTC start/end, exit code, stdout/stderr, source SHA, compiler gitlink, target model/AGNOS and GPU identity. Stop on OOM, GPU fault, thermal alarm, storage decline or source mismatch. Do not reuse CPU/LLVM or Dom captures and do not install an output from this phase.

Proposed **later, separately authorized** device shell sequence, after a hash-verified Git checkout and exact 19.9 toolchain have already been prepared in the isolated root. Set `MVL_BUILD_ROOT` to a reviewed isolated `/data` path, and `MVL_PYTHON` and `MVL_TOOL_BIN` to verified AGNOS 19.9 paths. None may point into `/data/openpilot`. Capture output in that same root. The command is deliberately conditional: it must not be run while the 19.9 image/dependency/capacity gates above are HOLD.

```sh
set -eu
test "$(cat /VERSION)" = 19.9
test -f /AGNOS
test "$(uname -m)" = aarch64
test -c /dev/kgsl-3d0
test -x "$MVL_PYTHON"
test -x "$MVL_TOOL_BIN/capnpc"
test -x "$MVL_TOOL_BIN/python3"
test "$(readlink -f "$MVL_TOOL_BIN/python3")" = "$(readlink -f "$MVL_PYTHON")"
test "$(git -C "$MVL_BUILD_ROOT/source" rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb
"$MVL_PYTHON" -B -c 'import SCons, capnp, numpy; print(SCons.__version__, capnp.__version__, numpy.__version__)'
df -Pk /data
mkdir -p "$MVL_BUILD_ROOT/tmp" "$MVL_BUILD_ROOT/cache"
cd "$MVL_BUILD_ROOT/source"
env PATH="$MVL_TOOL_BIN:/usr/bin:/bin" TMPDIR="$MVL_BUILD_ROOT/tmp" \
  timeout 3600 "$MVL_PYTHON" -m SCons -j1 --minimal cache_dir="$MVL_BUILD_ROOT/cache" \
  openpilot/selfdrive/modeld/models/dmonitoring_model_tinygrad.pkl \
  openpilot/selfdrive/modeld/models/driving_tinygrad.pkl \
  openpilot/selfdrive/modeld/models/driving_warp_1344x760_tinygrad.pkl \
  openpilot/selfdrive/modeld/models/driving_warp_1928x1208_tinygrad.pkl \
  openpilot/selfdrive/modeld/models/dm_warp_1344x760_tinygrad.pkl \
  openpilot/selfdrive/modeld/models/dm_warp_1928x1208_tinygrad.pkl
```

The interpreter equality check matters because modeld's SConscript launches the compiler using literal `python3` from `PATH`. The operator must verify `timeout`, `taskset` and the compiler's own imports, establish a measured working-set/reserve budget, and run external read-only monitoring before the last command. `mkdir` and SCons write inside the isolated root, so this sequence requires explicit device-side authorization. A failed preliminary check stops the sequence; it does not justify installing packages on the device.

Copy only six outputs into a new private evidence directory. Preserve each artifact SHA256/size, exact build log and AGNOS 19.9 image/rootfs identity. The current `mvl_model_artifacts.py record/verify` is explicitly pinned to 19.8.1 and must reject a 19.9 root; it cannot sign off the new target. A reviewed, exact 19.9 image-pinned validator and native inspector update are prerequisites to any later artifact PASS. Do not edit the 19.8.1 hash or label 19.9 outputs with it. Static capture validation would still not prove inference.

## Phase C — full product, only after six-output verification

Use a separate isolated staging checkout, clean cache and verified native AGNOS 19.9 toolchain for a full cold SCons product build only after the 19.9 provenance and compatibility gates pass. Do not run the destructive stock release script against an installed tree. Record build command, source commit, builder image digest, target architecture, compiler version, environment flags, process exit status and complete logs. After both validators are reviewed and pinned to a verified AGNOS 19.9 image, run static QCOM `verify` first, then bounded `timeout 300s python3 tools/release/inspect_native_product.py --source-root <exact-source> --staging-root <separate-product-stage> --qcom-manifest <manifest.json> --expected-source 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb > <private-inventory.json>`. The inspector hashes staged files and records ELF class, AArch64 machine, OS/ABI, interpreter, NEEDED, RUNPATH/RPATH and build ID. Review every dependency against the pinned AGNOS rootfs, package metadata, six model bytes and SCons build log. A static inventory PASS alone does not prove a complete build, load, inference or device boot.

After any changed product-source checkpoint, rerun the required combined regressions and independent exact-commit review. Keep C4-01–07 and C4-09–11 NOT_TESTED until an authorized install and actual bench evidence. C4-08 remains excluded while G06 is unregistered. C4-12 is `WAIVED_BY_OWNER / NOT_EXECUTED`; no restoration exercise is required. Do not activate experimental vehicle control or touch Panda/ECU policies. If the device remains unreachable or compilation is unauthorized, retain `PRODUCT_BUILD_INCOMPLETE` and this complete handoff.
