# Campaign 7 independent assessment status

## Codex read-only first pass
- Source reference: published Campaign 6 SHA 74f35f211668ec2035113c773de43a793eeb6375.
- Independently identified the P2 manifest-path blocking / symlink issue, source-backed.
- Reviewed R2–R8 boundaries and historical build/test evidence. It DID NOT execute new tests or review final C7 patch.
- Codex remediation subsequently ran into its usage limit and was not the basis for final acceptance. Patch validation performed separately with actual tools at committed code SHA.

## OpenCode + Qwen3-Coder
- R1 reviewed source at published C6. It generated contradictory or unsupported conclusions; the five leading claims were reconciled against implementation and new tests in CAMPAIGN7_R1_RECONCILIATION_20261108.md. Do NOT treat R1 report as independent PASS.
- R5/R6 source-only assessment reviewed fix commit 8705c12a07fc2e4c6a4c33d7ad441d113ab0cc66 and acknowledged nofollow/nonblocking protection and mandatory HOLD.
- Claimed a high-severity concurrent-file-write vulnerability without a concrete accepted invalid manifest or trust-anchor bypass. This remains an unverified threat-model limitation, not a demonstrated new P1/P2.
- New test-only successor commit adds a bounded FIFO replacement regression, clock rollback recovery regression; runtime verification belongs to Ubuntu test logs, not Qwen.

## Further boundary
The audit is an offline source and host-test qualification, not independent OEM, Panda, Comma4, B3 or full-product certification. Production release remains HOLD.


## Optional Qwen3.8 secondary assessment
OpenCode/Qwen3.8 27B IQ3 was launched in a separate model session against the same isolated Windows source. It generated **no usable findings or final verdict** and was stopped. Classification: INCONCLUSIVE_NOT_ACCEPTED. Its absence does not certify the code, diminish the source-backed initial P2 or turn unverified Qwen3-Coder claims into confirmed defects.

## Publication and reviewer limitation
The evidence branch was published and independently verified at 5b742df3ed6de7aa0c0291ca3ce84b3e8f50ea52. Tests were executed independently through Ubuntu host commands. Neither Qwen source review constituted a passing automotive release assessment.
