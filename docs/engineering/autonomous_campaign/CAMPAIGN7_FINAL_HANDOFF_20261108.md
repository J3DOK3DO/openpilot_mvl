# Campaign 7 — Verified final engineering handoff

**Repository:** J3DOK3DO/openpilot_mvl

**Branch:** codex/mvl-c7-offline-review-remediation-20261108

**Published reviewed-evidence commit:** 5b742df3ed6de7aa0c0291ca3ce84b3e8f50ea52 (authenticated Windows non-force Git push, exact remote SHA verified).

**New source tests/fixes:** held nonblocking nofollow manifest read; FIFO/symlink/type/identity/changed-content/swap tests; synthetic bridge producer-coherency limitation characterization; clock rollback recovery test; UI partial-draw characterization. No controller, Panda, ECU, CAN, Params, stock Honda ACC or physical device changes.

**Exact code test commit:** 0ab98cca292353080d1f230ea4d36146160834cb. 187 release-tool tests executed (178 passed, nine skipped); 99/99 UI and bridge tests; four recovery tests. Focused backup 19/19, included in release suite. Final evidence HEAD 5b742df3ed6de7aa0c0291ca3ce84b3e8f50ea52 also reran 187 release / 99 UI / four recovery successfully; no implementation changes from code commit.

**Independent scope:** Codex source-first R2–R8 audit detected P2 manifest opening issue, later mitigated and host-tested. OpenCode/Qwen3-Coder R1 review contained multiple source-contradicted false positives; reconciled in CAMPAIGN7_R1_RECONCILIATION_20261108.md. OpenCode/Qwen3-Coder R5/R6 review found no reproduced remaining integrity bypass, but raised unverified mutable-host concerns. Optional Qwen3.8 run produced no usable verdict. Do not claim independent hardware certification or production-ready status.

**Residual technical limitations:** Host-file verification requires an external trusted digest anchor and a trustworthy immutable source snapshot; concurrent IPC producer changes can split metadata from state across reads; optional badge label-draw failure can leave an unqualified partial background, no production supplier registered. Windows Python 3.9 baseline backup verifier is Linux-specific and cannot import os.O_DIRECTORY; this is not newly introduced by this patch.

**Release boundary:** B3 OWNER_DEFERRED, six genuine QCOM outputs 0/6; G10 full product NOT_BUILT; applicable physical Comma 4 checks 0/10; no approved package or installation. RC_NOT_INSTALLABLE / PRODUCT_BUILD_INCOMPLETE / HOLD.

**Operational state:** No active Campaign 7 lease, no pending code changes, no device access. Subsequent publication-record-only docs commit may advance HEAD without changing tested code. Do not reopen B3 except on new explicit owner instruction.
