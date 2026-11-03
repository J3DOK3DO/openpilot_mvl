# M0–M3 independent review, adjudication and promotion verdict

**Campaign:** 2025 US Honda Accord 11G Hybrid / MVL-first StarPilot status-bridge. **Code baseline:** MVL 376c44b5731b2655e5c2f301b73c9729eb499e91. **Scope:** strictly additive pure-Python read-only component, not an actual vehicle integration.

## Reviewer execution record

| Reviewer | Outcome | What was actually demonstrated |
|---|---|---|
| Codex GPT-5.6 Terra, lead implementation | IMPLEMENTATION PARTIAL, review not signed | Generated initial 5-module package and 44 test cases; command hit its 360-second limit before docs. Coordinator corrected MVL-native import, added factory tests and completed docs and qualification. |
| Codex GPT-5.6 Terra, read-only independent critique | ACTUAL ISSUES FOUND, session timed out | Reproduced accepting an arbitrary FeatureRegistry subclass whose active_topics() returns sendcan; also reproduced an unnecessary clock call on all-OFF reads. Tests that previously passed did not cover these exact cases. |
| Codex GPT-5.6 Terra, post-fix exact-file verification | COMPLETED, NO REMAINING DEMONSTRATED ISSUE IN SCOPED FILES | Returned verification that exact type checks block subclass spoofing; all-OFF return precedes clock/source access; only messaging.SubMaster is constructed. See CODEX_POSTFIX_VERIFICATION.md. |
| OpenCode + Ollama Qwen2.5-Coder 14B | INCOMPLETE | Standalone Windows invocation produced a zero-byte output and no Ollama inference. Only its assessment-specific processes were stopped. No Qwen source signoff claimed. |
| Direct Ollama Qwen2.5-Coder 14B | ADVISORY COMPLETE, not a source acceptance signature | Reviewed copied code/tests; 1,188 generated tokens, completed in 189.59 s. Output suggests eight items but they are already implemented, unsupported, or duplicate. Raw result is preserved under evidence/QWEN14B_BRIDGE_DIRECT_REVIEW_20261103.json. |

## Two independently reproduced issues and fixed acceptance

1. **Unexpected topic acceptance:** Initial `factory.py` and `adapter.py` accepted `isinstance(registry, FeatureRegistry)` and thus permitted a malicious subclass overriding `active_topics()` to return `sendcan`. Although SubMaster subscribes rather than transmits, this violates the status-only data boundary and could expose more messages. Fixed by requiring `type(registry) is FeatureRegistry` in both entry points. Regression tests now assert rejection of a forged subclass in both paths. Independent post-fix Codex agreed this blocks the reproduced case.
2. **All-OFF clock access:** Initial `ReadOnlyStatusAdapter.read()` called its injected clock before testing that all features are disabled. Fixed by evaluating the immutable active-topic registry first and returning `BridgeSnapshot(now_ns=0)` without calling the clock or source when no feature is enabled. A new test uses a forbidden clock function and opaque source. Independent post-fix Codex verified that the previous behavior is corrected.

## Qwen direct-result adjudication (no false-positive bug tickets)

| Qwen suggestion | Evidence-based disposition |
|---|---|
| `FeatureRegistry.values` external mutation risk | **Not reproduced.** `__post_init__` copies into new normalized dict and wraps it with MappingProxyType. Mutation of the caller's original mapping cannot alter the registry. Tests verify immutable values. |
| `SubMaster` might do I/O | **Expected only on explicit opt-in.** Factory rejects all-OFF before any cereal import or socket. Host native smoke explicitly created a read-only one-topic SubMaster. No publish path exists. |
| Timestamp not integer | **Already blocked.** `_timestamp` requires `type(value) is int` and nonnegative; invalid timestamps are intentionally rejected. |
| Use `isinstance` for registry validation | **Incorrect weakening.** Initial `isinstance` was precisely the reproduced bug; `type(registry) is FeatureRegistry` is retained. |
| Unknown feature keys not tested | **Already tested** in test_readonly_bridge.py (unknown, wrong case, wrong type, empty). |
| Snapshot rejection tuple allegedly mutable | **Not reproduced.** The projection is frozen and `rejections` is a tuple of frozen TopicRejection items. Replacing `()` with a tuple factory has no safety benefit. |
| Adapter clock I/O | **Already remediated** via return-before-clock when all OFF; injected monotonic getter is intentionally called for enabled feature validation. |
| Duplicate allowlist concern | **Same as registry concern**, and earlier fix plus new regression tests cover it. |

## Final scoped evidence

- Baseline frozen MVL host-native suite, on exact source pin: **1,140 passed, 613 skipped, 1 warning, 1,190 subtests passed**, exit 0. Skips are not passes.
- Read-only bridge tests on system Python: **51 passed / 0 failed / 0 skipped**, exit 0.
- Read-only bridge tests using existing MVL native Python environment: **51 passed / 0 failed / 0 skipped**, exit 0.
- Actual MVL native message integration smoke: `create_mvl_submaster(FeatureRegistry.from_overrides({device_status:True}))` created native SubMaster whose only subscription was **deviceState**; no publication or vehicle access.
- Static compileall: PASS. All existing vehicle-facing modules remain unchanged; no manager integration, route, Panda or Honda controller changes.

## Decision

**M0–M3 OFFLINE HOST PROTOTYPE: PASS** for frozen source, documented typed contracts, implemented and tested no-command bridge with all flags OFF and no pre-existing runtime edits. The two reproduced Codex issues were fixed and checked. Direct Qwen advisory contains no new source-backed blocker.

**Device and vehicle release: HOLD.** This package has not been connected to the production UI, rebuilt for AGNOS 19.8.1 ARM64, validated on Panda hardware, or checked against physical Honda ACC/CMBS/AEB. Neither AI reviewer provides device safety certification. The next authorized engineering step is a separate M4 non-actuating visual prototype based on typed snapshots, with its own native rendering, performance, warning priority, and exact-commit review.
