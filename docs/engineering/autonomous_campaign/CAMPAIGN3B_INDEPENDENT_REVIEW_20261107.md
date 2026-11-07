# Campaign 3B independent review — 2026-11-07

**Verdict: PASS_SCOPED_OFFLINE_IMPLEMENTATION / HOST_FEASIBILITY_OBSERVED / DEVICE_HOLD.**

An independent read-only Codex reviewer examined original implementation commit `912d34d60f6023146f50ed0a00536eb77c3ee402`. Initial **P2 NEEDS_FIX**: `_mount_id` decoded mountinfo spaces but not tab, newline or backslash escapes, which could miss a bind mount on the same device under awkward parent paths.

Codex fixed this at implementation commit **`7a15fc619fd676e030547570ac73f99ee2bac19e`**, decoding all four Linux mountinfo escapes and rejecting malformed mountinfo while accepting valid `nsfs` roots. The focused contract suite passed **11/11**, the clean full release-tool suite **117/117**, and recovery tests **4/4**. A separate fresh read-only Codex re-review of exact `7a15fc619` reported the issue resolved and found no introduced bug. These are review findings about host tooling only; no target safety certification is implied.

A separate Ubuntu host controller performed genuine bounded host experiments outside the Codex sandbox. Their JSON snapshots were retained without alteration and the contextual differences are documented in `CAMPAIGN3B_HOST_BOUNDARY_EVIDENCE_20261107.md`. Both experiments were benign and strictly host-only.

No vehicle-control/Panda/CAN/product source change, no Comma 4 write, no QCOM compilation, no full product build, and no installation occurred. Historical known-good identity is not reverified currently due Windows SSH authentication failure. Formal release remains **B2_HARDWARE_NOT_QUALIFIED / PRODUCT_BUILD_INCOMPLETE / HOLD**. This evidence branch is non-installable.
