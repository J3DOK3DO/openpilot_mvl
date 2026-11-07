# Independent B3/G10 Linux host-evidence review

**PASS_SCOPED — offline release engineering only. No device safety certification.**

Reviewed implementation and native container proof at commit 1ff4d0929f3fd0096e428b10b278c64c3b020b7c, descendant of published Windows release-gate checkpoint 2ea8980ff41cad5a0629381b2d6249c4d2538402. Separate read-only Codex review hash SHA256 41cd0e18ce8d658234971aac13ca18ae9b27667224975202e6e1cc2c1cb5b522. Initial P2 evidence gap (missing retained Docker execution provenance) was remediated by an authenticated local host Docker run with inspected HostConfig, stdout, exit statuses and matching exact source/ELF SHA256. The second reviewer found no P1/P2 discrepancy. Subsequent reconciliation of this review itself is documentation-only.

## Verbatim scoped verdict

**PASS_SCOPED** — read-only review of HEAD `1ff4d092` against `2ea8980f` found no P1/P2 provenance mismatch.

The [invocation record](/mnt/commadrive/MVL_B3G10_NATIVE_RECOVERY_20261107/docs/engineering/autonomous_campaign/COMBINED_B3G10_LINUX_NATIVE_INVOCATION_20261107.json:49) retains the exact Docker create argv, pinned ARM64 image ID, inspected network and resource settings, read-only source and AGNOS mounts, disposable output mount, and create, container, and cleanup exit codes of 0. Its stdout exactly matches the [execution log](/mnt/commadrive/MVL_B3G10_NATIVE_RECOVERY_20261107/docs/engineering/autonomous_campaign/COMBINED_B3G10_LINUX_NATIVE_EXECUTION_20261107.log:1). Both output hashes match the local fixture artifacts; source hashes, AGNOS image hash, and seven Gitlinks also match. The diff contains evidence and gate-test changes, with no product-code changes. Retained logs report 163 Linux tests run (154 passed, 9 Windows skips) and 4 recovery tests passed.

The [release report](/mnt/commadrive/MVL_B3G10_NATIVE_RECOVERY_20261107/docs/engineering/autonomous_campaign/COMBINED_B3G10_LINUX_HOST_REPORT_20261107.md:25) correctly limits this to **host-only compilation evidence**, without claiming signed independent attestation. **Device certification is absent:** Qualcomm B3 remains 0/6, the full G10 product is NOT_BUILT, physical C4 checks remain 0/10, the B2 waiver is for planning only, and release remains **HOLD**.
