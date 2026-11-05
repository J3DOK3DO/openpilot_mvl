# Recovery after interruption

1. Read `CAMPAIGN_STATE.json`, `MASTER_GATE_TRACKER.md`, `BLOCKERS.md`, and the latest entry in `RUN_HISTORY.md` before changing a gate decision.
2. Confirm `git rev-parse HEAD`, `git branch --show-current`, and the worktree status. Use `CAMPAIGN_STATE.json` for the active branch and recorded verified source commit; compare both with actual Git state. The original baseline remains `362c2fb6fed527e5f7e4737473b856b5ccf5766f`.
3. Review `TEST_RESULTS.json` and the cited campaign report. Re-run its exact test command if source, tests, or relevant environment changed. Record the actual commit, command, timestamp, exit code, and counts; never carry a previous PASS to a new commit without evidence.
4. For each gate, inspect its `GATE_FINAL_STATUS.md`, `FINAL_HOST_TESTS.log`, and `GATE_EVIDENCE_MANIFEST.json` under `../campaign_20261103/g*/` before promoting it.
5. Keep vehicle release on HOLD until native UI, security/hardware bench, AArch64 build/boot, physical Panda, OEM validation, integrated review, and protected rollback all have exact-commit evidence.
6. Append a dated decision to `RUN_HISTORY.md`, then update `TEST_RESULTS.json`, `MASTER_GATE_TRACKER.md`, `BLOCKERS.md`, `IMPLEMENTATION_MATRIX.csv`, and finally `CAMPAIGN_STATE.json` so its next action reflects the current gate.

If a test fails, record the command and failure in `TEST_RESULTS.json`, set the affected gate to FAIL or HOLD as warranted, describe the attempt in `BLOCKERS.md`, and leave release on HOLD.

## Executable startup check and ownership

Run `python3 docs/engineering/autonomous_campaign/campaignctl.py recover` before work. It compares the recorded branch and verified source SHA with Git, checks dirty paths and pending operations, and reports a state-only checkpoint commit separately. Exit code 2 means reconcile before proceeding. Inspect relevant running processes with `ps -eo pid,comm` and Git operation files if anything is pending. Never infer success from a terminated session.

Before a scheduled run, call `campaignctl.py recover`, inspect running processes, then `campaignctl.py claim-run`. Keep the returned token for the **entire run**, including milestone selection, implementation, tests, checkpoint and commit. Pass it to every modifying command as `campaignctl.py locked-run --token TOKEN -- <command>`; call `campaignctl.py heartbeat TOKEN` between long planning or review steps. End with `campaignctl.py finish-run TOKEN`. The token is local coordination state; never commit it. A second run cannot claim the lease, and commands without the current token cannot modify through this wrapper. The short command lock and persistent lease are both required.

After interruption, an active lease means HOLD for a new run. `claim-run --reclaim-stale` succeeds only after the 90-minute heartbeat expires and no command holds the OS lock; the former token becomes invalid. Inspect dirty files, pending operations, running processes, and test evidence before continuing. The reclaimed lease does **not** certify the prior work. Never delete a live lease merely to make progress. The lock and lease files are local and ignored by Git.

After a milestone: save implementation, run required tests, record exact commit and outcome, update state and history, commit verified changes, then name the next eligible action. A state-only checkpoint commit may contain only this directory; recovery recognizes it as one descendant of the recorded verified source commit. Any other SHA drift is an interrupted or external change to investigate.

## Publication status at 2026-11-03T17:03:48Z

The engineering branch was published to `J3DOK3DO/openpilot_mvl` at `40bc2805c00cd44ebcabee6830ecf96c3a1bd33c` using authorized Windows Git credentials, with remote ref verification. The Ubuntu local HTTPS remote remains unauthenticated; do not attempt repeated identical pushes there. Use the authorized Windows helper or configure legitimate credentials before subsequent non-force publication. Continue from the verified source checkpoint `daeffba203435502015ff037d436e3a2b89db1df` and keep all native/hardware safety gates HOLD. A docs-only publication checkpoint must not be mistaken for a new code-test PASS.

## Manual continuation checkpoint

The published `codex/mvl-starpilot-continuation` ref was independently verified at `0fb7b6a241df69ce5b6900f6f002baa2dfaab4d7`. The manual source candidate `codex/mvl-starpilot-manual` has tested code commit `6ea2fc99792a0f1a27d5e977fb6171637c5136cc`; the following docs-only commit is its state checkpoint. The original published worktree was not edited. Recover by checking the branch, HEAD, exact source ancestry, clean status, and `TEST_RESULTS.json`; rerun the 400-test isolated host/native command and G03 local IPC if dependencies or source changed. The x86 `libparams_c.so` symlink is temporary and must be removed after testing. Device, AGNOS build, Panda, OEM and protected rollback remain HOLD.

Use `NATIVE_HOST_SETUP.md` and `native_host_env.sh` to recreate the isolated host dependency path; verify every pinned SHA and remove the temporary library link after tests.

## G10 continuation checkpoint at 2026-11-04T07:01:57.237828+00:00

The PR #1 head `b070247` was left unmerged. New isolated branch `codex/mvl-g10-continuation` has tested source `162391f22567774166a6bd02024a65d969f63b59`; its following campaign documentation commit may be docs-only. Run `campaignctl.py recover`, compare the recorded source SHA to HEAD and check both the exclusive lease and process list. Read `G10_BUILD_EVIDENCE_20261104.json`, `G06_G08_READONLY_EVIDENCE.json` and the exact 401-test entry in `TEST_RESULTS.json`. The build worktree contains copied pinned submodule contents and ignored ARM64 outputs; use a clean exact-commit host checkout for the native x86 combined suite so G03 source-availability expectations remain valid. Preserve the ARM64 artifact at `/mnt/commadrive/MVL_G10_BUILD_ARTIFACTS/libparams_c_162391f.so`. Never infer a full cold product build or device qualification from the library build or SCons dry-run.

The `../campaign_20261103/CAMPAIGN_MASTER_REPORT.md` is historical baseline evidence. For current 401-test, native ARM64 library and gate decisions, use this autonomous-campaign state, test record, tracker and G10 evidence.

## Comma 4 restricted-profile continuation

Start from published `e5909a36765105ad4a3bfe6407ffb3ed71ea1d5e` in new branch `codex/mvl-comma4-release-rc-20261104`; PR #1 and prior branches remain unchanged. Read `COMMA4_RELEASE_PROFILE.md` before interpreting G11/G12. They are not applicable only to this non-actuating profile, not safety PASS. `PRODUCT_BUILD_INCOMPLETE` is the current release classification. On restart run `campaignctl.py recover`, inspect lease/process/dirty state, reconcile exact source/test SHA, then continue eligible offline work. Do not install or activate a candidate without separate authorization and protected backup/restore readiness.

## Restricted comma 4 checkpoint at 2026-11-04T16:23:12.443198+00:00

The exact tested source is `feee77a81dbefe4655c5d60c459362005e8e588d` on `codex/mvl-comma4-release-rc-20261104`. The following campaign documentation commit may be one docs-only descendant. On recovery check `campaignctl.py recover`, lease ownership, pending operations, process list, `git status`, and `TEST_RESULTS.json` before resuming. Re-run the 442-test pinned native host command and G03/recovery probes if source or environment changes; the temporary x86 library symlink must be absent afterward. The full product build remains HOLD because source-matched QCOM artifacts and hydrated pinned dependencies are unavailable. Read `COMMA4_DEVICE_TEST_PLAN.md` before any separately authorized device work. No comma 4 tests, installation or known-good restoration occurred in this run.

## G10 closure checkpoint 2026-11-05

Start from `codex/mvl-g10-closure-20261105` exact tested source `7e0015b5b74e2b6372cd7dae0122815cbd491e43`; the following campaign-only checkpoint commit may be one descendant. Run `campaignctl.py recover`, inspect lease/process/dirty state, and confirm the source SHA and seven pinned submodule heads. The build worktree under `/tmp/mvl-g10-closure-20261105` has 283 hydrated selected LFS assets. If temporary storage is gone, restore only exact pinned commits and selected object hashes as recorded in `G10_FINAL_BUILD_CLOSURE_20261105.md`; do not assume prior success. The clean exact-source host checkout passed 443 tests, eight IPC paths and four recovery tests; rerun if source or environment changes. AGNOS graph log and source preflight JSON are persisted here. No full build/package or comma 4 device test exists.
