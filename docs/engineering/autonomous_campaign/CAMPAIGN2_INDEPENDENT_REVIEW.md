# Campaign 2 independent review

An independent reviewer inspected the exact Campaign 2A tooling commit `9f16b4e8e314fe35c75af21705dce7220c77a52d`. Initial verdict was **NEEDS_FIX**: the host guardian could report completion or heartbeat abort while a same-group child continued running; the read-only telemetry wrapper could print `probe_complete=1` after a Python failure. Both defects were reproduced without device access.

Commit `947e326ecb221ccb2640d2bb2f8f051f230c34fd` terminates live process-group members after leader exit and abort, adds descendant regressions, and propagates telemetry failure. Reviewer re-reproduced both initial cases and found the descendants terminated; 11 then-focused tests passed. Reviewer also reproduced a **remaining limitation**: if the guardian itself is SIGKILLed after a fixture has forked, the leader's parent-death signal does not kill its descendant. This is a failed host crash-containment case, not device proof. The proposed device watchdog gate stays UNKNOWN/HOLD. No device pilot is enabled.

Final exact-commit review of the complete documentation checkpoint: **PENDING**. No independent B3 compilation or G10 product review is possible because they were not executed. Preserve the hardware/release HOLD regardless of a host documentation review.

## Separate post-interruption technical assessment — 2026-11-07

A separate GPT-6 assistant session (not the Codex authoring or its prior review agent) inspected the committed Campaign 2 Python hardware gate, host guardian, representative ABI inspector, PowerShell read-only probes, the negative-path tests and the source-boundary diff at exact implementation/documentation checkpoint `aa4d39abb4693187fcbd2f4b1356ba67cfaad267`. It independently reran the clean worktree release-tool suite **106/106 PASS**, recovery suite **4/4 PASS**, JSON duplicate-key/parse validation for nine Campaign 2 evidence files, and `git diff --check`. On the separate Windows host, both PowerShell scripts parsed with zero errors and ran in **plan-only** mode without any Comma 4 connection.

**Assessment: PASS_OFFLINE_EVIDENCE_AND_PUBLICATION_SCOPE / HARDWARE_NO_GO.** The checkpoint can be retained and published as a non-installable engineering evidence branch. This is an assessment of the bounded offline tooling, test evidence and documented limits; it is NOT a complete independent vehicle-device, Qualcomm compiler, runtime or physical safety qualification.

Open findings that prohibit device execution:

1. The host guardian now kills lingering process-group descendants when the guardian remains alive and the worker exits or aborts. However, an unexpected guardian process death with a forked descendant is not shown to be contained by a fail-safe *independent* kernel-level boundary. The single worker leader has a parent-death signal; grandchildren need not inherit that protection. This is not qualified as a device watchdog.
2. `/data` ext4 project-quota prerequisites were not observed, no aggregate alternative has been proven, and CPU cgroup memory limits do not demonstrate Qualcomm GPU allocation/driver containment.
3. `pandaStates` alone did not establish reliable concurrent parked and disengaged vehicle-state evidence; `carState` and `controlsState` were absent in the passive observation.
4. ABI evidence is a **representative direct-dependency static check**, not transitive ABI, a full product build or AGNOS 19.9 runtime loading.
5. No device staging, compilation, installation, safe cleanup or hardware failover test was performed.

For the published documentation-only descendant, the implementation tests refer to `aa4d39a` (it contains the identical code tree to the last tested `947e326ec`). This review is distinct from the Codex reviewer and explicitly does **not** close the hardware NO-GO gates or increase acceptance beyond 12/25.
