# C17 hardening review adjudication

This continuation preserves commit `6f4196ebbc47383f57fadb186047790eca9ac6db` and the original independent review in history. It does not convert a scoped offline review into device, vehicle, or security certification.

## Confirmed defect

The pre-hardening `c17_ipc_redirect.c` accepted `/msgq_` names containing further slashes. `shm_unlink("/msgq_/../../../victim")` could therefore escape `C17_MSGQ_ROOT` and delete a controlled canary. The independent reproduction is accepted as source-specific and valid.

The hardened shim:

- rejects empty, slash-containing, backslash-containing, `.` and `..` C17 POSIX-shm suffixes with `-1` and `errno=EINVAL`;
- never falls back to host shm for an invalid `/msgq_…` name while C17 redirection is active;
- redirects ordinary msgq files only for the exact `/dev/shm/msgq_${OPENPILOT_PREFIX}/<endpoint>` namespace;
- rejects traversal, namespace mismatch, and symlinked root/event/queue directories;
- opens redirected final files with `O_NOFOLLOW`;
- retains valid native `deviceState` msgq behavior within the unique private root.

Focused preload regressions cover the exact `shm_unlink` reproduction, malicious `open` and `open64`, invalid names, symlinked roots/child directories, and valid native-style names. These are controlled host tests, not a general-purpose sandbox proof.

## Other allegations

- Publisher frequency is already constrained to `1 <= hz <= 100`; no change required.
- The launcher already requires an absolute existing output directory and rejects a symlink; individual result names are also no-overwrite checked. This is scoped path validation, not a general filesystem security guarantee.
- `params_mode` is already an `argparse` choice; no change required.
- `open64` already honors a negative `redirected()` result; the new regression explicitly covers it.
- Font symlinks are intentionally rejected by the release audit. This is fail-closed provenance behavior.
- Cleanup suppresses expected kill races and waits for known children. Tests verify no surviving campaign processes, but this is not a categorical process-containment guarantee.
- The `requests` monkeypatch and Python socket guard are defense-in-depth. They are not a verified network namespace, kernel firewall, or comprehensive network sandbox. Xvfb is still launched with TCP disabled and proxy variables are removed.

## IPC labeling

Only a continuously observed, fresh synthetic publisher receives `HOST_FIXTURE_CONTINUOUS_FRESH`, explicitly limited to the isolated host fixture. Publisher absence is `DEGRADED_NO_PUBLISHER`. A stopped publisher is `DEGRADED_PUBLISHER_TERMINATED_*`, with freshness recorded. Neither degraded result nor host-fixture freshness qualifies real device IPC.

Physical Comma gates P1–P7 remain NOT_RUN. Device installation is false and Option B remains HOLD.
