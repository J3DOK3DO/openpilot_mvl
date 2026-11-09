# Campaign 8 independent Qwen source review handoff

**Status: PENDING independent Qwen review.** This file is a handoff, not a review verdict. Coordinator owns the separate reviewer and publication; no Qwen call, device access, GitHub push or campaign-lease action occurred in this run.

## Review snapshot

- Isolated branch: `codex/mvl-b3-g10-r0-cleanrelease-20261109`.
- Implementation and clean-HEAD test commit: `00d83d6d1fdfcca93a237564c0efd29bd0fc2276`.
- Frozen product: `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`; tinygrad gitlink `92b742f711c7d216fd3ed7a46a30a959e3c43bd4`; AGNOS image `80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7`.
- Inspect the final documentation successor commit separately and compare its source diff with this code commit. Release classification must stay `ENGINEERING-HOLD / NOT-INSTALLABLE`.

## Files and questions for the reviewer

1. Review `tools/release/mvl_model_artifacts.py`, `qcom_b3_prepare.py`, `qcom_b3_admission.py` and the two changed tests. Check same-descriptor static parse/hash, bounded streaming opcode count, `O_NOFOLLOW`/file type/size handling, directory count, JSON cap, bad byte and race paths. Static hashes and self-reported receipts must never authenticate Qualcomm execution or promote B3.
2. Review `docs/engineering/autonomous_campaign/C8_G10_YUV_LINK_20261109.sh`. Confirm pinned image ID, source/rootfs read-only mounts, no network, 1.5 GiB/one CPU/64 PIDs/300 seconds, isolated output and no binary execution. The real output in the external artifact directory is ELF64 AArch64; library SHA-256 `8c2df07ab6b6e9840b4f09e3177172559ad2cfe1caf69dc8ec35fe56dd4b2472`, raw build log SHA-256 `25e7703b2cf188aee1a87ff98ab72b44a4875468206935498ebdf49ef0920b82`. Check DT_NEEDED `libc.so.6` and absent RPATH/RUNPATH. This is one YUV link, not G10 product.
3. Check frozen `SConstruct`, `panda/SConscript`, `modeld/SConscript`, and the six-target plan. Panda graph writes generated headers, so any future cold build needs an isolated writable staging copy. Confirm the conditional command cannot be mistaken for an executed full build and cannot run against frozen source.
4. Check `combined_b3g10_gate.py`, `combined_rc_readiness.py`, `inspect_native_product.py` and their negative tests. Six fake receipts, false full product, wrong source/AGNOS/ELF, symlink/truncation and missing physical checks must stay HOLD. Existing RC code 2 is intended; 254 Params DENY, Galaxy OFF and StarPort exclusion are required, with target runtime proof outstanding.
5. Review the six C8 deliverables for consistent actual versus absent artifacts. The external `C8_INPUT_OUTPUT_SHA256SUMS` is SHA-256 `2004455688c98f9627395f863033d8f01886b9b07273b99db6517303281d4825`. No installer, model output, device receipt, Panda firmware or clean-install backup exists.

## Reproduction and acceptance boundary

The frozen-source preflight raw JSON SHA-256 is `58cb1fa76444d7eafebdf87275e817cdb887df8328ed817ae8f2559822667327`. At clean implementation commit, release suite: 200 run, 191 passed, nine skipped; focused native: 10/10; recovery: 4/4. Logs and hashes are in `C8_TEST_RESULTS_20261109.json`. RC JSON SHA-256 is `4f5316a799f8aed53821af9cdc91c8a130c4126c7ca19fcda387636574144249`; it reports `RC_NOT_INSTALLABLE`, `install_allowed=false`, B3 0/6, G10 `NOT_BUILT`, physical 0/10. Re-run the same commands at final clean HEAD, record the final SHA and raw log hashes externally, then return an independent source verdict with actionable findings. Any review approval remains scoped to offline engineering and cannot authorize device compilation or installation.
