# Combined B3/G10/RC offline campaign — 2026-11-08

**Engineering branch:** `codex/mvl-combined-b3g10-rc-recovery-20261108`, created from published `2489f58b97c915547ec94c03a073da0dbe45eaa9`. **Release decision:** `PRODUCT_BUILD_INCOMPLETE / RC_NOT_INSTALLABLE / HOLD`. Frozen product source remains `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`; the engineering diff contains no `openpilot`, `panda` or `SConstruct` changes. There was no device contact, source staging, QCOM compilation, installation, CAN transmission, ECU/Panda change or vehicle-control activation in this campaign.

## Recovery and immutable inputs

The starting GitHub branch returned the requested `2489f58` SHA. A separate lease-owned worktree was created; old worktrees and leases were preserved. The frozen checkout HEAD and tinygrad HEAD matched their pins. Fresh SHA-256 checks matched the AGNOS 19.9 raw image `80d93733…602c7`, handoff manifest `998b4173…e4abfcab9ee4`, handoff archive `37a82b74…f0ba3d60fe`, two ONNX assets, stock modeld SConscript and two tinygrad compiler scripts. The rootfs reports `VERSION=19.9`. Ubuntu had about 19 GiB free in /tmp and 21 GiB on /mnt/commadrive. No relevant compiler process was found at recovery.

## C1 — non-actuating integration

The frozen product contains the existing lane-centering implementation and default `LaneCentering=0`; this campaign made no active-control change. Read-only StarPilot bridge/view-model, G05 native status, Honda/MVL warning priority, G06 default-OFF prototype and G08 catalog remain at their previously accepted host scope. The 254-key Params crosswalk file was freshly parsed: 254 entries, 254 DENY, zero approved, all read and write flags false. The RC admission tool itself labels these as historical or not independently reverified by that tool. No StarPort-specific product integration or approved non-actuating acceptance contract was found in the inspected frozen source; it is not invented here. Actual comma 4 UI, status timing, warning, startup/fault fallback and Honda/OEM behavior remain physical HOLD.

## C2 — Qualcomm

The exact six stock targets, pinned tinygrad commit `92b742f711c7d216fd3ed7a46a30a959e3c43bd4`, ONNX hashes and QCOM flags were rechecked against the frozen source and existing B3C plan. Historical local model captures belong to other source/product contexts and cannot substitute. The frozen stock model directory has **0/6 genuine QCOM outputs**; the Ubuntu host has no authenticated Qualcomm KGSL compiler provider. B2 project waiver permits planning only: the device lacks demonstrated aggregate storage, live parked-state, GPU memory, thermal and independent abort safeguards. Compilation remains `NOT_EXECUTED`. ONNX graph input/output shape parsing was not repeated because an authenticated local ONNX parser is unavailable; file identities and compiler recipe hashes were checked.

## C3 — AGNOS native product

The existing bounded host AArch64 non-QCOM YUV fixture was rehashed: object `23d4a8e4…fc68`, shared library `f586ce52…cd5`, ELF64 AArch64 with build ID `deeaa7656aa818878c71ae52a4ca72a75a853545`. The retained Docker invocation records an exact image ID, read-only source/rootfs mounts, no network, 1 GiB RAM, one CPU, 64 PIDs and exit 0. It is historical host component evidence, not a new build in this campaign. The six QCOM inputs are absent, so no complete cold ARM64 product was attempted. Full ELF dependency closure, target runtime load and installable package remain `NOT_BUILT/NOT_TESTED`.

## C4/C5 — admission and installation preparation

`tools/release/combined_rc_readiness.py` derives a fail-closed offline release matrix from the hash-pinned B3 gate. It rejects unexpected promoted claims, treats local artifact presence as unverified metadata, emits a plan-only installation sequence, and exits 2 for HOLD. Its pure mock rehearsal covers preflight, backup, stage, switch and health failures; every path preserves the known-good reference and performs no device I/O. C4-09's prepared host command was corrected to AGNOS 19.9. The later device procedure requires an exact six-name inventory and hash comparison. Neither the plan nor its tests is an installation or rollback exercise on a Comma 4.

Exact reviewed tooling commit and test commands are in `COMBINED_CAMPAIGN_TEST_RESULTS.json`; the independent review and remaining code/documentation limits are in `COMBINED_CAMPAIGN_INDEPENDENT_REVIEW.md`. The 20-item equally weighted engineering matrix counts 11 completed preparation/qualification items (**55% engineering completion**); blocked or excluded items count zero. This is separate from the inherited formal scoped acceptance **12/25 = 48%**, ten applicable physical C4 checks **0/10**, and final release approval **HOLD**. C4-08 is conditional N/A only while G06 remains unregistered; C4-12 remains `WAIVED_BY_OWNER / NOT_EXECUTED`. G11/G12 remain conditionally N/A for the unchanged non-actuating profile.

## Next eligible action

An authenticated Qualcomm-native provider with independently verified storage, vehicle-state, GPU/thermal, memory and abort safeguards is required before any bounded model compilation. Actual device staging/compilation and later installation each require separate explicit owner authorization. Until six authenticated outputs and the full product exist, continue only offline tooling and source-backed validation; preserve the known-good installation.
