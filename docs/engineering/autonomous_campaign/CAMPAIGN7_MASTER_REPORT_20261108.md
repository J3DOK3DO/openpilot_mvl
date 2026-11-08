# Campaign 7 — independent review and bounded offline remediation

**Branch:** codex/mvl-c7-offline-review-remediation-20261108
**Baseline:** 74f35f211668ec2035113c773de43a793eeb6375
**Tested code commit:** 0ab98cca292353080d1f230ea4d36146160834cb
**Vehicle target:** 2025 US Honda Accord 11G Hybrid / Bosch-C CAN-FD / Comma 4.
**Status:** OFFLINE_ENGINEERING_REMEDIATED_WITH_LIMITATIONS / PRODUCT_BUILD_INCOMPLETE / HOLD.

## What was done
1. OpenCode/Qwen3-Coder on Windows read the actual pinned source. Its R1 assertions about accepted rejected-snapshots, clock rollback and timestamp mutation were not borne out by code; see reconciliation. No vehicle-safety PASS inferred.
2. A separate Codex read-only review of R2–R8 identified one actionable P2 vulnerability in tools/release/offline_backup_preflight.py: opening a supplied manifest before checking its file type could block on a FIFO and follow symlinks.
3. A new isolated branch implemented held-descriptor, nonblocking, nofollow, regular-file and inode/metadata checks, bounded reads and preserved SHA-256 digest verification. No release-admission promotion is possible.
4. Focused negative tests cover manifest FIFO with no writer, symlink, file/directory identity change, changed content, and regular-file-to-FIFO replacement between lstat and open.
5. Read-only bridge synthetic-producer test demonstrates that producer and metadata maps are not atomic across concurrent writes; it is **documented and not fixed by speculation**. Another host test characterizes optional UI partial background when gui_label raises. Clock rollback/recovery test counters unsupported R1 allegations.
6. No new AGNOS image, B3 models, Comma4 hardware interaction or native product build was attempted. Previously accepted YUV/msgq/socketmaster static component evidence remains historical, not runtime-qualified.

## Exact regression evidence at code commit
- Release-tool unit suite: 187 executed; **178 passed, nine platform skips, zero failed**.
- Host UI + bridge + view suite: **99 passed**, zero failed.
- Campaign recovery tests: **4 passed**, zero failed.
- Focused backup tests: **19 passed** and are included in the release-tool suite; not double counted.
- Offline RC gate: exit 2, decision RC_NOT_INSTALLABLE, install_allowed=false, QCOM 0/6, full product NOT_BUILT, applicable physical checks 0/10.
- Log SHA-256 and command lines are captured in CAMPAIGN7_TEST_RESULTS_20261108.json.

Initial failures from a dirty intermediate checkout and a sparse missing-module test environment were corrected and are not evidence of a production regression. The final exact-code committed tests passed. The Linux-specific backup validator already required os.O_DIRECTORY before this campaign; Windows Python 3.9 cannot import it and is not a supported functional validation target.

## Reviewer limitations and genuine residuals
- Independent Qwen source inspection is not equivalent to executing tests. R1 contained multiple false-positive high-severity claims.
- Manifest digest must have an external independent trusted anchor. Verification of a mutable host copy is not a guarantee of an immutable snapshot under hostile concurrent writers.
- UI label-draw partial background and status producer/consumer coherent snapshot remain unqualified. Optional status UI and bridge remain default OFF and non-actuating.
- Historical 254 restricted Params DENY requirements remain unchanged; no protected code paths were edited.

## Protected boundaries
Diff from baseline to reviewed code includes ONLY the backup verifier and its tests and two read-only UI/bridge test files. Zero source diff to Panda, ECU, CAN transmission, engagement, vehicle controller, braking or steering logic. This is not proof of actual OEM road behavior.

## Release classification
B3: DEFERRED_BY_OWNER, verified Qualcomm model outputs 0/6.
G10 full product: NOT_BUILT.
Comma4 physical acceptance: 0/10.
Installation: NOT_AUTHORIZED.
Final release: RC_NOT_INSTALLABLE / PRODUCT_BUILD_INCOMPLETE / HOLD.

## Handoff
Continue independent reviewer reconciliation and publish only after scope and tests are verified at final committed HEAD. Preserve original Campaigns 1–6 and known-good installation. Do not reopen B3 or waive release prerequisites.

## Final disposition
Reviewed engineering evidence published and verified at 5b742df3ed6de7aa0c0291ca3ce84b3e8f50ea52 on codex/mvl-c7-offline-review-remediation-20261108.
The dedicated Campaign 7 lease was released. Optional Qwen3.8 second reviewer provided no usable result and is explicitly INCONCLUSIVE. The completed work remains OFFLINE TESTED WITH REVIEW LIMITATIONS; not a production-ready release.
