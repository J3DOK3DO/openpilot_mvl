# Campaign 3B mountinfo independent-review remediation

Base commit: `8219f82144f5bf049299620e6084d8555d7b040a`.

The independent reviewer found that `_mount_id` decoded only `\040` in the mountpoint field. A same-device bind mount below a parent containing an escaped tab, newline, or backslash could therefore be missed, allowing `validate_write_coverage` to return `SIX_AREAS_ONE_ACTUAL_MOUNT` incorrectly.

The host contract now decodes all four Linux mountinfo path escapes (`\040`, `\011`, `\012`, `\134`) in root and mountpoint fields. It rejects unknown or incomplete escapes and malformed mountinfo entries before returning a covering mount ID. A valid `nsfs` root such as `net:[...]` remains accepted. The regular `/proc/self/mountinfo` path is exercised by the existing coverage test.

Deterministic tests mock mountinfo for parents containing each escaped character, verify that six real child directories pass without a child bind, then add a same-device child bind entry and require rejection. Awkward parent paths and malformed root, mountpoint, and structural entries fail closed. No host mounts were created.

Verification commands:

```text
python3 -m unittest -q tools.release.tests.test_campaign3_host_contracts tools.release.tests.test_campaign3_offline
python3 -m unittest discover -s tools/release/tests -p 'test_*.py' -q
python3 -m unittest -q docs.engineering.autonomous_campaign.test_campaignctl
git diff --check
```

The full release suite includes inspector tests requiring a clean source checkout, so its authoritative result is the run after committing this remediation. The coordinator owns independent re-review and separate host evidence.

Decision remains **B2_HARDWARE_NOT_QUALIFIED / PRODUCT_BUILD_INCOMPLETE / HOLD**. QCOM remains **0/6**; cold native product **NOT_BUILT**; physical C4 **0/10**. This remediation makes no device qualification claim and involved no device contact, compilation, production source change, sudo, or GitHub push.
