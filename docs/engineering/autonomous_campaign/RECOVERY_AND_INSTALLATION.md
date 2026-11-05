# Recovery and installation boundary

Use `RECOVERY.md` and `campaignctl.py recover` to resume offline engineering. Confirm the actual Git HEAD, branch, dirty files, active process and lock owner before any new milestone. Re-run uncertain tests on the exact source commit.

**Installation HOLD:** No clean-install or device activation procedure is authorized by the current evidence. A future package requires artifact hashes, exact target ABI/dependencies, a tested protected rollback path, device boot/resource evidence, Panda safety identity, Honda OEM collision-mitigation validation and release-owner approval. Do not treat a successful build or script syntax check as installation approval. Preserve known-good source and recovery evidence.

## 2026-11-05 owner amendment

For `COMMA4_NON_ACTUATING_MVL`, C4-12 physical restoration is WAIVED_BY_OWNER / NOT_EXECUTED; automated rollback and rollback stress are NOT_REQUIRED. This supersedes the prior tested protected-rollback prerequisite above. The owner will manage factory reset and reinstall of the recorded previously known-good branch if needed. The exact known-good branch and official device factory-reset procedure must be confirmed with the owner before any separately authorized installation. No factory reset or reinstall is part of this offline campaign. Full package integrity, native build, device boot/UI/IPC/runtime/security tests, independent review and separate installation authorization remain mandatory.

Official comma 4 factory-reset reference: [comma.ai Flash your comma](https://comma.ai/support/flash-your-comma). The vendor says flashing erases device software and data; this is a reference for owner-managed recovery only, not an instruction to perform it in this campaign. The actually installed known-good branch/SHA remains unrecorded and must be confirmed before any separately authorized installation. The vendor page describes stock openpilot setup and does not itself certify reinstall of a custom known-good branch.
