# AGNOS 19.9 / QCOM build readiness — 2026-11-06

**Decision: PRODUCT_BUILD_INCOMPLETE / HOLD.** Release profile remains `COMMA4_NON_ACTUATING_MVL`. This checkpoint changes offline planning and read-only diagnostics only. It does not qualify an AGNOS 19.9 binary, compile six Qualcomm captures, build a product, or authorize device mutation. The fresh device facts below were supplied from authenticated Windows SSH; this Ubuntu worktree did not contact the device. The older Ubuntu `NO_ROUTE_TO_HOST` result remains historical, not a contradiction.

## Evidence and version contract

| Item | Evidence | Assessment |
| --- | --- | --- |
| AGNOS device | `/VERSION=19.9`, `/AGNOS` present, `aarch64`, device-tree `comma mici` | OBSERVED; comma four model alias accepted |
| GPU/compiler | `/dev/kgsl-3d0`, `/usr/bin/clang`, `/usr/bin/clang++`, Python 3.12.3, pinned tinygrad Git link `92b742f7...` with `compile_onnx.py` | OBSERVED; GPU presence is not compilation success |
| Source pin | `launch_env.sh` defaults to AGNOS 19.9; `openpilot/common/hardware/comma/agnos.json` pins image component hashes | PASS_HOST source inspection; image hash is not a verified local 19.9 rootfs |
| Historical build | 19.8.1 image/rootfs, SCons graph and one `libparams_c.so` were previously checked | HISTORICAL_REFERENCE_ONLY, not 19.9 qualification |
| Artifact and product validators | `mvl_model_artifacts.py` requires 19.8.1 `/VERSION` and image SHA; `inspect_native_product.py` requires the same manifest | BUILD_TARGET_MISMATCH for 19.9, not a verified ABI break |
| Six exact-source QCOM captures | None exist; CPU/LLVM and Dom packages are ineligible | HOLD |

`SConstruct` selects `comma_arm64` only on AArch64 with `/AGNOS`, uses Clang, `-mcpu=cortex-a57`, target `/usr/lib/aarch64-linux-gnu`, vendored `acados`, `capnproto`, `ffmpeg`, `json11`, `ncurses`, `zeromq` and `zstd`, Cython and NumPy. Its default on-device SCons cache is `/data/scons_cache` with a nominal 2,000,000,000-byte pruning threshold; a later isolated build must override `cache_dir` to avoid the installed cache. Pruning is not a hard peak-space guarantee. The 19.8.1 environment provided `/usr/local/venv/bin/python3`, SCons and `capnpc`; the PATH omission previously caused a failed native library build. This is evidence of a possible 19.9 PATH issue, not proof that 19.9 has that venv or identical packages. `pyproject.toml` requires Python 3.12.3+, SCons, `pycapnp==2.1.0`, NumPy 2+, and comma-deps wheels; `uv.lock` pins SCons 4.11.1 and AArch64 wheel identities. No exact 19.9 package inventory, libc/libstdc++/FFmpeg/Cap'n Proto ABI comparison, compiler version, or GPU runtime test exists. Do not use the 19.8.1 sysroot as 19.9 compatibility proof.

The revised `readonly_comma4_preflight.py` reports `OBSERVED_COMPATIBILITY_PENDING` and `BUILD_TARGET_MISMATCH` for 19.9, and treats 19.8.1 as a historical reference. It still refuses unknown versions, no recognized actual CPU or GPU sensor reading, unresolved required tools, low fixed-copy space and missing identity. It checks bounded alternate SCons/capnpc executable locations and the default Python SCons module without installing packages. A failed PATH lookup alone is not absence; the reported `scons_module=no` and absent tested paths remain **unresolved**, because the search is not exhaustive. The script remains read-only, uses no device-writing commands and was tested with mocked SSH responses. Do not invoke Ubuntu SSH in this campaign.

## Isolated capacity assessment

The supplied `/data` availability is **9,256,568 KiB = 8.83 GiB** at 90% usage. The trusted source tar is **223,006,720 bytes** and the manifest sums **219,518,275 bytes** across 4,372 file entries. Storing both requires at least **442,524,995 bytes (422.0 MiB)**, before filesystem overhead, Git metadata, logs or anything compiled. This is a measured lower bound, not a build estimate. The handoff cannot serve as a Git checkout by itself. The two ONNX inputs and selected LFS bytes are included in the source file sum; separate verification/staging copies add space.

| Capacity term | Current basis | Planning treatment |
| --- | --- | --- |
| Archive plus extracted selected source | 422.0 MiB file bytes | Known minimum; add Git checkout metadata and verification overhead |
| SCons cache | Nominal prune threshold 2.0 GB on hardware | Reserve at least that much if enabled; measure peak, set isolated `cache_dir` |
| Six outputs, GPU compiler scratch, TMPDIR, Python tooling, logs | No measured peak | REQUIRED_CAPACITY_UNKNOWN; size before transfer/build |
| Full cold product staging and duplicate evidence copies | No measured peak | Separate later budget; no product-build PASS |
| Free-space reserve | 2 GiB minimum planning stop; 4 GiB safer recommended target | Additional reserve beyond measured peak, not a claim of OEM safety |

With a 2 GiB reserve and fixed copy, 6.42 GiB remains for *all* other uses. Reserving a nominal 2.0 GB cache and a safer 4 GiB free-space target leaves only about 2.55 GiB for checkout metadata, six outputs, tooling, scratch and logs. Thus the observed 8.83 GiB can accommodate the archive and selected source, but **does not yet prove an isolated six-target build fits**, and cannot be extended to a full product build. Before any approved transfer, inventory size of the exact Git checkout, offline wheel set/venv, cache and measured trial output/scratch budget on an independent matching host; require `free /data >= sum of remaining measured peak allocations + reserve` continuously. Stop if this cannot be demonstrated. No known-good installation or user data may be removed for space. No-delete alternatives are an approved external matching QCOM builder, an approved external storage route with measured I/O behavior, or deferring until a device with sufficient free capacity is available; each device-side route needs its own authorization.

`/tmp` is a 150 MiB tmpfs and is unsuitable as an assumed compilation work area. A later authorized build should create `TMPDIR` only under its isolated `/data` build root, after proving the disk budget. `/dev/shm` had 1,795,704 KiB available, but it is shared RAM and not a substitute for persistent storage. `MemAvailable` was 2,481,948 KiB (2.37 GiB); start at one job, monitor memory and GPU faults, and only raise concurrency with observed headroom. Rootfs had about 445 MiB free and must not host tooling. Ubuntu has roughly 19 GiB free on root and 34 GiB on the engineering volume, but no compatible GPU.

Thermal `lmh-dcvs-00/01` zones reached 75,000 mC and appear to report limits/virtual state. The hottest supplied actual CPU reading was `cpu0-silver-usr=49,400 mC`; actual GPU temperature was not supplied. The preflight now separates limit/virtual zones from CPU/GPU readings. Its 70 °C actual-sensor rule is a conservative planning stop, not a chip rating. Sustained-build thermal behavior remains unknown.

## Offline dependency bootstrap/check plan for 19.9

1. On the host, obtain a trusted AGNOS 19.9 image/rootfs with verified component hash and `/VERSION`, without changing the device. Record AArch64 ELF interpreter, libc/libstdc++ symbols, Clang, `capnpc`, Python, SCons, `pycapnp`, NumPy, comma-deps packages, GPU userspace libraries, and exact wheel hashes. Compare against repository `pyproject.toml`, `uv.lock`, `SConstruct`, `SConscript` and the historical 19.8.1 inventory. A missing 19.9 image is a prerequisite HOLD.
2. Use an isolated host rootfs copy and read-only package inventory first. Prepare offline wheel/tool inputs only from hashes that match the 19.9 target Python and AArch64 ABI. Test import/tool resolution and a small native link/load against that rootfs in an isolated builder. Do not infer GPU compilation from emulation or a 19.8.1 binary.
3. Before any separately authorized device action, use bounded read-only checks for the actual 19.9 Python/venv, SCons module and executable, capnpc path, clang version, package versions, library resolution, GPU driver/userspace identity, free space, CPU/GPU sensor types, and exact installed branch/SHA. The supplied absence on default PATH/system Python does not establish actual absence. Do not run ad hoc apt/pip/uv installs on the comma.
4. Only after image, ABI, dependencies and capacity are reviewed, prepare a new exact 19.9 image-pinned artifact recorder and product inspector. Preserve the 19.8.1 validator/hash as historical evidence; do not relabel a 19.9 capture with 19.8.1 provenance.

## QCOM continuation and gates

The handoff manifest SHA256 is `998b417374930b75338b7ef8be9b3739d3e9e4d130c39ae0aa10e4abfcab9ee4`; its tar SHA256 is `37a82b744d079c0a130b3f88e24ba4d56b7aa5db4c0bc709449ed4f0ba3d60fe`. Seven gitlinks and 283 selected LFS assets were verified in the earlier source-only campaign. The pinned tinygrad source and Qualcomm GPU node make a native route **plausible**, not ready. `openpilot/selfdrive/modeld/SConscript` requires exactly two ONNX model captures and four warp captures with `DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1`; `SKIP_TINYGRAD_COMPILE` must be unset. No CPU/LLVM or Dom substitutions are valid. Keep raw build logs, environment allowlist, exact source/gitlink/AGNOS/GPU identity, exit status, output SHA256/size and later inference evidence. A six-output static PASS, when eventually available, would still precede a complete product build and bench qualification.

| Gate | State | Reason |
| --- | --- | --- |
| Revised offline preflight and focused tests | PASS_HOST | Mocked 19.9/19.8.1, aliases, limit zones, low/unknown disk and tool paths |
| Device model, AGNOS, GPU, resource snapshot, installed branch | OBSERVED | User-supplied Windows SSH, read-only; owner approval to replace installation absent |
| AGNOS 19.9 rootfs/ABI and dependency match | HOLD | No verified 19.9 image or exact package inventory |
| Isolated six-target capacity | HOLD | Cache/output/tool/TMP peak unknown |
| Six exact-source QCOM outputs and full product | HOLD | No outputs or cold build |
| Device install, inference, boot and applicable C4 checks | NOT_TESTED | No device mutation or execution in this campaign |
| C4-08 | N/A while G06 live service is OFF/unregistered | Reopen if service is enabled |
| G11/G12 | Conditionally N/A | Strict non-actuating profile only |
| C4-12 | WAIVED_BY_OWNER / NOT_EXECUTED | No restoration exercise or PASS claim |

No route, VIN, private key, token or personal data is in these reports. The known-good installation was only read, never treated as replacement approval. Device-side source copy, QCOM compilation and installation are separate future authorizations. Exact later commands and stop criteria are in `QCOM_DEVICE_BUILD_HANDOFF_20261106.md`; its six-target command is conditional on verified 19.9 tooling/capacity and must use an isolated `TMPDIR` and cache. No full product build PASS or device qualification is claimed.

## Offline verification and publication checkpoint

At code/documentation commit `bace68ce273d66e42ce872d54e03a59d9c43c7bb`, the clean worktree passed `python3 -m unittest discover -s tools/release/tests -p 'test_*.py' -q` (**32/32**) and `python3 -m unittest -q docs.engineering.autonomous_campaign.test_campaignctl` (**4/4**). The focused preflight/model artifact run passed **17/17**; the 13 handoff/recovery units passed separately. The source-only package verifier checked **4,372/4,372** archived files against the externally retained manifest hash and tar hash. `git diff --check` and JSON parsing passed. The inherited 444 host tests at `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` were **not rerun** in this checkpoint. The first inspector test attempt failed only because its fixture requires a clean source tree while this checkpoint was still uncommitted; its clean-tree rerun passed within the 32-test suite. No target build or device test was run.

A distinct read-only reviewer inspected the pre-commit diff, independently reran the nine preflight tests, found four documentation issues, and confirmed all four were fixed before commit: explicit `-j1`, supersession of archived 19.8.1 instructions, accurate thermal wording, and exact Python interpreter resolution for SConscript child commands. No actionable issue remained in that review. This is independent source review, not AGNOS 19.9 target qualification.

GitHub `HEAD` was reachable, and the proposed new branch was absent. A non-force HTTPS push of this branch failed with `could not read Username for 'https://github.com'` because the Ubuntu environment lacks usable credentials. The local commit remains intact and **remote publication is NOT_DONE**. Do not use Ubuntu SSH. A Windows helper with authenticated GitHub access can publish the same local branch after mapping this isolated worktree:

```powershell
$worktree = '<Windows path to this isolated worktree>'
git -C $worktree status --short
git -C $worktree rev-parse HEAD
git -C $worktree push https://github.com/J3DOK3DO/openpilot_mvl.git HEAD:refs/heads/codex/mvl-agnos199-qcom-readiness-20261106
git ls-remote --heads https://github.com/J3DOK3DO/openpilot_mvl.git refs/heads/codex/mvl-agnos199-qcom-readiness-20261106
```

Require a clean status and compare the final `rev-parse HEAD` to the expected checkpoint SHA shown by the host before pushing. This publishes only the new branch; it does not modify PR #1 or any protected branch.
