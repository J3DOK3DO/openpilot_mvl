# C9 independent Qwen handoff

**Review requested; no Qwen verdict recorded by Codex.** Review the exact local committed branch `codex/mvl-c9-b3-g10-r0-combined-20261109` against pinned starting HEAD `d5f13720fca5d2557320cbf90728d93e3086cf4a`. The coordinator owns Qwen execution and any GitHub publication. Do not promote B3, G10 or R0 from a source review alone.

Inspect `tools/release/c9_b3_pilot.py`, `c9_b3_receipt.py`, `c9_b3_windows_pilot.ps1`, `c9_r0_stage.py`, `test_c9_campaign.py`, and the C9 documents and CDM build script. Focus on source/path symlink and trust boundaries, exact six target plan and flags, live monitor fail-closed behavior, systemd scope kill/timeout/resource limits, Windows SSH quoting, pickle static parsing versus authentication, Panda graph side effects, and HOLD package content. Re-run the committed-head tests and verify the raw hashes in `C9_TESTS_20261109.json` and `C9_G10_BUILD_20261109.json` under `/mnt/commadrive/MVL_C9_B3_G10_R0_ARTIFACTS_20261109`.

The independent decision must keep these separate: source review, static QCOM byte inspection, independently authenticated native QCOM compilation, full cold product/ELF and Panda firmware, physical C4 qualification, trusted backup/rollback, and installation approval. In this campaign only the first two are prepared, and no actual QCOM output exists. The CDM proof is an isolated ABI artifact. Expected release result is `RC_NOT_INSTALLABLE`, `install_allowed=false`, B3 0/6, G10 NOT_BUILT and physical 0/10. Preserve the nine platform skips as skips.

If review finds a defect, send exact file/line, impact, reproducer and recommended fix to the coordinator. No independent reviewer sign-off, device execution, GitHub push or lease transfer is represented by this handoff.
