# Campaign 2 independent review

An independent reviewer inspected the exact Campaign 2A tooling commit `9f16b4e8e314fe35c75af21705dce7220c77a52d`. Initial verdict was **NEEDS_FIX**: the host guardian could report completion or heartbeat abort while a same-group child continued running; the read-only telemetry wrapper could print `probe_complete=1` after a Python failure. Both defects were reproduced without device access.

Commit `947e326ecb221ccb2640d2bb2f8f051f230c34fd` terminates live process-group members after leader exit and abort, adds descendant regressions, and propagates telemetry failure. Reviewer re-reproduced both initial cases and found the descendants terminated; 11 then-focused tests passed. Reviewer also reproduced a **remaining limitation**: if the guardian itself is SIGKILLed after a fixture has forked, the leader's parent-death signal does not kill its descendant. This is a failed host crash-containment case, not device proof. The proposed device watchdog gate stays UNKNOWN/HOLD. No device pilot is enabled.

Final exact-commit review of the complete documentation checkpoint: **PENDING**. No independent B3 compilation or G10 product review is possible because they were not executed. Preserve the hardware/release HOLD regardless of a host documentation review.
