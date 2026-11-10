# C17 independent review handoff

Disposition: offline host-bench candidate; physical-device acceptance remains HOLD.

The reviewer must independently reproduce hashes and tests. The campaign author does not assign an independent PASS. Preserve all C15 and Qwen reports unchanged; evaluate C17 as an additive, scoped change.

## Review scope

- Confirm the worktree parent and C17 commit identities.
- Inspect `c17_standalone_ui.sh`, `c17_standalone_ui.py`, `c17_device_state_publisher.py`, and `c17_ipc_redirect.c`.
- Re-run the AST audit proving the only `PubMaster` service and only send target are `deviceState`.
- Confirm synthetic `deviceState.started=false`, no manager launch, no network transport, Xvfb `-nolisten tcp`, private Params, and `/tmp`-redirected msgq backing.
- Verify the authentic UI class imports, 17 font hashes, six host/ARM native hashes and ELF architectures, archive traversal/symlink checks, and execution from an unpacked archive.
- Review lifecycle evidence for bounded close, WM_DELETE close, SIGTERM, empty/malformed Params, publisher absent/terminated, missing Xvfb, untrusted source/assets, wrong/missing runtime, and read-only output behavior.
- Confirm C15/Qwen evidence was neither overwritten nor rewritten.
- Confirm no vehicle module, CAN, controller safety gate, Panda, firmware, protected source, rootfs, or physical device was changed.

## Required reviewer output

Record reviewer identity/tool, exact reviewed commit and archive SHA-256, commands, raw exit codes, findings, limitations, and one disposition: `PASS_SCOPED_HOST_BENCH`, `FAIL`, or `NEEDS_WORK`. A scoped host PASS must not be presented as Comma GPU, backup/restore, product, vehicle, or installation approval.

Current reviewer disposition: `INDEPENDENT_REVIEW_PENDING`.
