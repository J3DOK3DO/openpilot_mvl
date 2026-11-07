# B3C independent review remediation — 2026-11-07

## Status and boundary

Remediation of the four independent reviewer findings is implemented for separate re-review before publication. No native QCOM provider, trusted signature key, or independently signed execution manifest is available. This work grants no B2 safety acceptance, B3 completion, device usage, or G10 promotion. The owner waived B2 documentation for planning only.

## Findings and remediation

| Finding | Reviewer observation | Remediation | Regression evidence |
| --- | --- | --- | --- |
| HIGH1 | Structurally fabricated pickle captures and made-up receipts could return issue-free `B3_STATIC_6_OF_6_PENDING_AUTHENTICATION` and CLI exit 0. | Every nonempty record set returns `UNVERIFIED_NATIVE_COMPILER_EXECUTION` and `NATIVE_OUTPUT_PROVENANCE_NOT_AUTHENTICATED` issues and nonzero CLI status. `static_candidates` is separate from `b3_verified_artifact_count`, which remains 0; `b3_completed_6_of_6` remains false. Zero records may return issue-free `PREPARED_NO_QCOM_DEVICE`. | `test_fabricated_six_remain_unverified_even_if_byte_verifier_passes`; `test_cli_fabricated_records_exit_nonzero`; `test_prepared_is_not_safety_approval`. The fabricated records include arbitrary `0`-filled 64-character receipt hashes and a monkeypatched byte verifier. |
| HIGH2 | Seven SHA-256 receipt strings and literal `PASS_INDEPENDENT_REVIEW` established syntax only. | `receipt_authentication_status` and every receipt field label say `SELF_REPORTED_NOT_AUTHENTICATED`. No attestation or independent review is claimed verified; no mock validator was added. | `test_fabricated_six_remain_unverified_even_if_byte_verifier_passes` checks the status and persistent issues. |
| MEDIUM | Audit did not bind exact execution plan, QCOM flags, unset `SKIP_TINYGRAD_COMPILE`, stock argv/cwd, recipe/compiler hashes, ONNX hashes, prerequisites, or run path. | CLI checks exact input bytes against SHA-256 `6a493a0d9418f62310ee9a0f33d8e50ade4d5dc768cd54ec9c20ad45eaf3cd6e` before decoding. Audit loads that hash-pinned checked-in file and compares the entire plan, including source inventory and all nested fields. | `test_every_plan_field_is_pinned` changes source commit, flags, prerequisites, paths, hashes, argv/cwd and output; `test_cli_rejects_altered_plan_bytes_before_decode` rejects even whitespace-only byte changes. Tests use the checked-in plan fixture. |
| LOW | Report and recovery state said `/dev/dri` was absent on the host. | Report and recovery distinguish restricted Codex sandbox visibility from unrestricted Ubuntu host inventory. The host has `/dev/dri/card0` and `/dev/dri/renderD128`, is `x86_64`, and has no `/dev/kgsl`; DRM nodes do not prove QCOM execution. | Documentation review against the supplied independent reviewer observation. |

## Acceptance limit

Static `qcom_capture` inspection, record hash matching, compiler exit values, and receipt strings are self-reported or structural observations. Independent cryptographic authentication of actual native QCOM execution and independent quality review would require a trusted mechanism bound to source, AGNOS, run, and all six output hashes. None is configured. All supplied capture records therefore fail admission. The separate independent re-review remains outstanding.

## Test commands

Focused: `python3 -m unittest tools.release.tests.test_qcom_b3_admission -v`.

Full release: `python3 -m unittest discover -s tools/release/tests -v`.

Recovery: `python3 -m unittest docs.engineering.autonomous_campaign.test_campaignctl -v`.

After the code commit, the clean checkout run passed 123/123 release tests and 4/4 recovery tests. The focused admission suite passed 6/6 tests.
