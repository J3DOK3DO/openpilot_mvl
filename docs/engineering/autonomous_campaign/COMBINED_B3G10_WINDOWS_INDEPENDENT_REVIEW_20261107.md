# Combined B3/G10 Windows offline independent review - 2026-11-07

**PASS_SCOPED: offline release-gate tooling only.** The first independent Codex review identified three P2 path-handling findings; these were remediated by the Codex lead. A fresh separate read-only Codex session reviewed all seven final files, found no remaining actionable P1/P2, and maintained release HOLD.

The coordinator independently executed **37/37 focused Windows Python 3.9 tests (PASS)**; the read-only reviewer did not independently rerun the full writing fixture suite. Older Unix-specific test-suite errors on Windows remain documented, not promoted to passes. Native Qualcomm models remain **0/6**, full G10 product **NOT_BUILT**, Comma 4 checks **0/10**, and owner B2 waiver is for planning only. No vehicle-device access or installation occurred.

Review input branch: codex/mvl-b3g10-windows-offline-gates-20261107
Reviewed base HEAD: b708816ab845c1a4b4988fc1e210cf167be43254
Separate reviewer output SHA-256: 2138136c716620dea29bb58dd099b72e5de58719e2d6123764eb54607d7a00f5

## Reviewed file hashes

- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_GATE_20261107.json: faea8b422667a987106a6c3c4c7c7cba046a0b213fcc2baf79c9d2dfc699e81c
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_OFFLINE_REPORT_20261107.md: c1894ace3a08b12e8c4a056d009d327b7a0df4329c51e734661565721650a71a
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_RECOVERY_20261107.json: 65b1147e4656dce3861994f58cb5bc86475d491bf00f6c22f9a59c29e534b475
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_TEST_LOG_20261107.log: e6bd056ba837db4de1b6dbd82c8ef86a6952504c4bfca67ada8957650b7b62cd
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_VALIDATION_20261107.json: 3c4eb8afce0c36de7c2eee7a4ce433db5f3fda71f0db4a29462d20aaee5dbccf
- tools/release/combined_b3g10_gate.py: 6ed73290528776e71cf2cbf4a4773a84567b5a673b15d83fd15ab9146f775754
- tools/release/tests/test_combined_b3g10_gate.py: e3054604a6afea52d8e53d482acd5343c0bddb2bed1e8b2fd5544ddef42f4521

## Verbatim read-only Codex re-review

**PASS_SCOPED — no actionable P1/P2 found** across all seven untracked files at `b708816ab845c1a4b4988fc1e210cf167be43254`.

- Windows holds every ancestor through all six metadata checks. `FILE_LIST_DIRECTORY` with read-only sharing excludes write access required for reparse mutation; no-follow opens and held-handle validation prevent reparse traversal. Native regressions cover existing writers and denied `GENERIC_WRITE`.
- POSIX pins with `O_PATH|O_NOFOLLOW`, checks regular-file type, then reopens the exact inode through `/proc/self/fd`. Unsupported facilities fail closed; special devices receive no read-open. POSIX coverage is mocked on Windows.
- All six recorded evidence hashes match; both pinned inputs equal their HEAD blob bytes. Fresh offline evaluation exactly matches the recorded gate.
- The verified log records **37/37 passing**, matching all current test names. Fresh rerun was blocked by read-only fixture creation; no independent rerun success is claimed.
- Older suites correctly report Windows errors: admission **4 passed/4 errors/1 skipped**, subset **19 passed/2 errors**, recovery **4 errors**. No full-suite success is claimed.

Release remains **BLOCKED_NATIVE_B3_AND_G10_NOT_INSTALLABLE**: real QCOM **0/6**, full cold G10 **NOT_BUILT**, C4 **0/10**, B2 planning waiver **not safety passed**.

Seven files and HEAD remain unchanged. No device contact, product execution, compilation, staging, commit, push, or web search.

The lead report's statement that Git staging was blocked describes the earlier Codex sandbox. This coordinator-owned review record accompanies the subsequent authorized engineering commit. Neither review nor commit is a product release or hardware qualification.

## Canonical Git-blob provenance reconciliation

The SHA256 values above were verified against original Windows CRLF working bytes when the independent review was performed. Git normalized those same reviewed files to canonical LF at initial scoped commit 457f811d64ead32c07c4128ce898a30f4d47cbe4. The following SHA256 values represent actual canonical publishable Git blob bytes (report and recovery include later documentation-only corrections), with no non-newline changes to reviewed code or tests.

- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_GATE_20261107.json: ecf85b3f6a32f53db073009090e381f01fa5092b2f536c9b74040f6e211e0f75
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_OFFLINE_REPORT_20261107.md: c6bba846f41585650c59d1de52bf40c24ddb7a65df57990784ea1ac9bc61aa77
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_RECOVERY_20261107.json: 43a49bb3a23f893aeca4e789179bde4186fb8eff700455d8288accd65f281f1b
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_TEST_LOG_20261107.log: 4101dc4193b5c4890ac093e0ff09117b1bc5f5469b144cd7ac97b97496436ef1
- docs/engineering/autonomous_campaign/COMBINED_B3G10_WINDOWS_VALIDATION_20261107.json: 3a82d019aa6cc0d4fff47afb6dd5de1abff9cb53bba8f41139bf02b323c5bee1
- tools/release/combined_b3g10_gate.py: 1dec6943cac4c975716e3c1f9cd3976e0dbd7198d2bb8e6c2669082431c87476
- tools/release/tests/test_combined_b3g10_gate.py: 898af3d346aeb6cfd26e1b7f42303bf881f93365548488a7a4d434b4ace8768d

Historical validation and precommit test logs remain intact as time-scoped evidence. The recovery evidence_sha256 map now hashes canonical LF. Neither the documentation reconciliation nor reviewer scope is a real QCOM capture, full G10 product, physical test or installation qualification.
