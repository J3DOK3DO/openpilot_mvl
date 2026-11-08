# Combined offline installation readiness — plan only

**Decision: NOT_INSTALLABLE.** The candidate has 0/6 authenticated QCOM outputs, no complete AGNOS 19.9 product/package, no accepted physical C4 checks, no current installed-branch confirmation, and no installation approval. `python3 -m tools.release.combined_rc_readiness` prints a static matrix and exits **2** by design. It does not connect to or write a device. `rehearse()` is an in-memory mock, not a device recovery script.

## Required future entry checks

1. Verify the approved engineering branch, exact frozen source lineage, seven pinned Gitlinks, tinygrad and two ONNX hashes. Reject any modified active-control/Panda/ECU/CAN-transmit boundary.
2. Verify the six *genuine* stock QCOM outputs by exact name, source binding, SHA-256, captured compiler exit, backend provenance and separate target quality review. Reject extra or substituted model captures.
3. Verify a complete cold ARM64 product from AGNOS 19.9: package tree hashes, every native ELF architecture/build ID/needed library/RUNPATH, versioned and transitive dependencies, and target runtime checks. A representative library is insufficient.
4. On a separately authorized physically isolated bench, independently confirm the exact installed known-good branch/SHA and owner-managed recovery route. The historical observed reference is `sp-honda-dev-202608` / `a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1`; it is **not currently reverified**.
5. Establish a reviewed backup plan for owner data and known-good software. Validate any migration against the 254 restricted Params DENY list; no protected key may be read or written for MVL integration.
6. Confirm parked/disengaged and hardware isolation, full package/identity checks, a fresh release review and explicit installation approval before any device write.

## Conditional execution and failure response

Only a later separately reviewed installer may stage and activate a complete package. Do not use `build_release.sh` for this offline campaign: its text includes worktree removal, CPU policy writes, Panda build and force pushes. After an approved install, complete C4-01–07 and C4-09–11 with raw logs, UI video, timing, fault/fallback, model hashes and resource observations. C4-08 is conditional on G06 registration; C4-12 remains owner-waived and unexecuted.

The mock failure sequence is preflight → backup → stage → switch → health. A failure at any step stops the modeled flow and reports `STOP_OWNER_RECOVERY_REQUIRED`; no automatic device rollback is claimed. The current owner waiver makes automated rollback and restoration stress `NOT_REQUIRED` for this non-actuating profile. The owner retains responsibility for any future factory reset and known-good branch reinstall. The official factory-reset reference is retained in `RECOVERY_AND_INSTALLATION.md`; no reset or reinstall was performed here.

**Outstanding physical prerequisites:** full B2 resource and live-state safeguards; complete product; current device and known-good identity; ten applicable C4 results; reviewed installation package and separate owner approval. There is no runnable device installation script in this checkpoint because those prerequisites are absent.
