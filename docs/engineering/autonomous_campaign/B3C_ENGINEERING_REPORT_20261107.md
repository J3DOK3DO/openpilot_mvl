# B3C Qualcomm offline engineering report — 2026-11-07

## Decision

**PREPARED_NO_QCOM_DEVICE; 0/6 genuine exact-source stock QCOM artifacts.** B3 source planning is complete on the available Ubuntu x86_64 host. No native QCOM compilation, device transport, staging, installation, active vehicle control, Panda CAN, or G10 promotion occurred. The owner's B2 disposition is **OWNER_WAIVED_B2_OUTSTANDING_REQUIREMENTS_FOR_PLANNING_ONLY**, **NOT_SAFETY_ACCEPTED**, **NOT_PASSED**. Missing hard resource bounds and proof of a parked vehicle remain blockers.

## Exact inputs and preflight

- Engineering checkout: branch `codex/mvl-b3-qcom-offline-qualification-20261107`, ancestor `9d61a7e7f10e88f5236ca6628bbb32167c8f2547`.
- Frozen source: `/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263` at clean `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`; read-only `preflight_readonly.py` returned `PASS`, no changed or dirty paths, 1,813 checked blobs, seven pinned materialized gitlinks. Tinygrad link and checkout: `92b742f711c7d216fd3ed7a46a30a959e3c43bd4`.
- Stock recipe `openpilot/selfdrive/modeld/SConscript` SHA-256 `07499bf98dafa501025e08f71c1819787b5dac9f681d443cb0557a1a9d0d7097`; compiler scripts `compile_onnx.py` SHA-256 `512571a84dc7931a07713a81b342e5087c41b173edea2d9a3b209fb83c5ab340`, `compile_warp.py` SHA-256 `97a6814fde7f16e1ce265c6b6388cd5799c8e2f8969ac78cfc4fd5a929b1921d`. Stock graph and exact six output paths are in [B3C_SIX_TARGET_VERIFIED_PLAN_20261107.json](B3C_SIX_TARGET_VERIFIED_PLAN_20261107.json).
- Real hydrated ONNX bytes: `dmonitoring_model.onnx` 7,844,499 bytes, SHA-256 `dee5a294e8afaacc9295ac5d100e00733ecac278e79264b96331e40a3ede1b04`; `driving_supercombo.onnx` 60,918,562 bytes, SHA-256 `65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce`. These are not LFS pointers.
- Source handoff `manifest.json` SHA-256 `998b417374930b75338b7ef8be9b3739d3e9e4d130c39ae0aa10e4abfcab9ee4`, `source.tar` SHA-256 `37a82b744d079c0a130b3f88e24ba4d56b7aa5db4c0bc709449ed4f0ba3d60fe`. The tar is a source transfer, not a Git identity substitute.
- Authentic AGNOS 19.9 component manifest found at frozen source `openpilot/common/hardware/comma/agnos.json`, SHA-256 `c581f89ea1fa16814c4f1965cb2113d2e8c628dfa88d5f210bf2f0917cad6693`. `qcom_b3_prepare.prepare()` checked it against the raw 4,718,592,000-byte ext4 image SHA-256 `80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7` and extracted rootfs `/VERSION` = `19.9`; existing `AGNOS199_IMAGE_PROVENANCE.json` independently records reconstruction and rootfs extraction. The full image was hashed once in this campaign by the helper.
- Host `x86_64`, VMware SVGA II Adapter. The restricted Codex sandbox did not expose `/dev/dri`; the unrestricted Ubuntu host has `/dev/dri/card0` and `/dev/dri/renderD128`. Neither DRM node proves a native QCOM provider; the host has no `/dev/kgsl`. A host CPU/LLVM compilation cannot establish native QCOM output. Bounded searches of the frozen source, AGNOS work area (excluding rootfs), and handoff found no six stock target outputs. Two sunnypilot warp captures under `openpilot/sunnypilot/modeld_v2/models` have a different target path and no B3 source-matched native provenance; both are excluded.

## Conditional native execution handoff — commands documented, not executed

The exact command vectors, source directory and isolated output paths are recorded in the plan. On a separately authenticated native QCOM provider with verified aggregate hard quota, free-space reserve, independent live parked-state monitoring if connected to a vehicle, actual GPU/CPU thermal and error telemetry, tested memory ceiling and abort/recovery, use `DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1`; unset `SKIP_TINYGRAD_COMPILE`. The first target is:

```sh
cd /data/mvl-builds/4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb/pilot-1234567890abcdef/source
env -u SKIP_TINYGRAD_COMPILE DEV=QCOM IMAGE=1 FLOAT16=1 NOLOCALS=1 JIT_BATCH_SIZE=0 OPENPILOT_HACKS=1 PATH=/usr/local/venv/bin:/usr/bin:/bin TMPDIR=/data/mvl-builds/4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb/pilot-1234567890abcdef/tmp HOME=/data/mvl-builds/4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb/pilot-1234567890abcdef/home PYTHONDONTWRITEBYTECODE=1 /usr/local/venv/bin/python3 -m SCons -j1 --minimal cache_dir=/data/mvl-builds/4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb/pilot-1234567890abcdef/cache openpilot/selfdrive/modeld/models/driving_warp_1344x760_tinygrad.pkl
```

After independent review of the pilot's genuine QCOM exit, static capture bytes, hard quota, memory, thermal, GPU error, and abort evidence, the ordered remaining target arguments to the same command prefix are:

```text
openpilot/selfdrive/modeld/models/dmonitoring_model_tinygrad.pkl
openpilot/selfdrive/modeld/models/driving_tinygrad.pkl
openpilot/selfdrive/modeld/models/driving_warp_1928x1208_tinygrad.pkl
openpilot/selfdrive/modeld/models/dm_warp_1344x760_tinygrad.pkl
openpilot/selfdrive/modeld/models/dm_warp_1928x1208_tinygrad.pkl
```

Each target requires its own actual native exit code, byte hash, static `qcom_capture` inspection (never unpickle), source/AGNOS/backend provenance, resource record, and independent quality review. A warp pilot does not bound the driving ONNX model. `qcom_b3_admission.py` records the B2 planning waiver separately. Its admission is fail closed for every nonempty record set: static candidates are separate from verified artifacts, and all supplied receipt fields remain `SELF_REPORTED_NOT_AUTHENTICATED`. Provider authentication needs an independently trusted cryptographic mechanism that is not available here.

## Independent review remediation before publication

The four findings and exact regression tests are recorded in [B3C_INDEPENDENT_REVIEW_20261107.md](B3C_INDEPENDENT_REVIEW_20261107.md). HIGH1: fabricated pickle captures and invented receipts previously could yield issue-free `B3_STATIC_6_OF_6_PENDING_AUTHENTICATION` with exit 0. Admission now emits `UNVERIFIED_NATIVE_COMPILER_EXECUTION` and `NATIVE_OUTPUT_PROVENANCE_NOT_AUTHENTICATED` for every nonempty record set, exits nonzero, and keeps verified count at zero even when six static byte checks pass. HIGH2: seven SHA-256 strings and `PASS_INDEPENDENT_REVIEW` are syntax checks only; the report explicitly labels them `SELF_REPORTED_NOT_AUTHENTICATED`, with no fake signature validator. MEDIUM: the supplied plan is checked against the frozen SHA-256 before JSON parsing and the audit compares every plan field with that trusted file, including flags, unset `SKIP_TINYGRAD_COMPILE`, argv/cwd, paths, hashes, ONNX identity, and prerequisites. LOW: the DRM inventory above distinguishes sandbox visibility from unrestricted host observation. Focused tests: `test_prepared_is_not_safety_approval`, `test_every_plan_field_is_pinned`, `test_fabricated_six_remain_unverified_even_if_byte_verifier_passes`, `test_cli_fabricated_records_exit_nonzero`, `test_cli_rejects_altered_plan_bytes_before_decode`, and `test_bad_records_never_complete`. This remediation is pending a separate independent re-review and is not safety acceptance or B3 completion.

## Next environment and test evidence

Use an external Qualcomm bench with verified hardware and hard resource controls, or an authenticated trusted native QCOM environment that can supply the six exact-source stock outputs and reviewable execution receipts. If a vehicle is involved, the unresolved device safety controls remain mandatory. No on-device compilation should begin under the current B2 risk state.

Commands run here: `python3 tools/release/preflight_readonly.py --repo /mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263 --commit 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`; `python3 tools/release/qcom_b3_prepare.py --source /mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263 --handoff /mnt/commadrive/MVL_QCOM_HANDOFF_4b25263_20261105 --agnos-image /mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/system-19.9.ext4.img --agnos-rootfs /mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs --agnos-component-manifest /mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263/openpilot/common/hardware/comma/agnos.json --run-id 1234567890abcdef`; `python3 tools/release/qcom_b3_admission.py --plan docs/engineering/autonomous_campaign/B3C_SIX_TARGET_VERIFIED_PLAN_20261107.json`; `python3 -m unittest discover -s tools/release/tests -v`; `python3 -m unittest docs.engineering.autonomous_campaign.test_campaignctl -v`. The initial release run found two inspector tests that require a clean engineering checkout while the new files were untracked. The original clean post-commit rerun passed **120/120** release tests; after this remediation's code commit, the full clean checkout suite passed **123/123** release tests and campaignctl recovery passed **4/4**. The focused admission suite passed **6/6**. The plan SHA-256 is `6a493a0d9418f62310ee9a0f33d8e50ade4d5dc768cd54ec9c20ad45eaf3cd6e`. Recovery state is in [B3C_RECOVERY_STATE_20261107.json](B3C_RECOVERY_STATE_20261107.json).

## Final verification and classification

At the reviewed implementation checkpoint `836962c2ab4ad885aa9d60d49e82a661ee650581`, the completed offline work passed **126/126** release-tool tests and **4/4** recovery tests. The independent re-review identified and resolved additional P2 input-handling cases: oversized file, changed bytes between validation and parsing, and device special-file opens. The final CLI uses pre-open regular-file validation, a no-follow descriptor, a 1 MiB maximum read, and hashes the same parsed bytes. A separate code re-review found no introduced regression. **B3 is prepared but not completed: 0 of 6 genuine QCOM captures**. Owner B2 waiver remains for planning only, no safety acceptance or claimed device readiness. No hardware operation, native compilation, install or G10 promotion occurred.
