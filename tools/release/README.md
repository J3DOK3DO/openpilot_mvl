# openpilot releases

## Offline source preflight

`preflight_readonly.py` checks an exact committed source tree without building,
packaging, fetching, cleaning, or changing device state. It reuses the existing
`release_files.py` selector only to inspect its file list. A `PASS` means this
limited source preflight passed; it is not a product build or release decision.

Run from a clean, isolated engineering worktree:

```sh
python3 tools/release/preflight_readonly.py --repo . --commit "$(git rev-parse HEAD)" --baseline <approved-source-boundary-commit> > preflight.json
```

The JSON reports exact HEAD, modified paths, committed blob sizes, Git LFS
hydration, pinned submodule checkouts, selected file count, and restricted
control/Panda/manager changes. Exit status is 0 for `PASS`, 1 for `HOLD`, and
2 for an inspection error. Keep the generated report outside the source tree
or rerun after committing it, since untracked output causes `HOLD`. Review
the complete changed-path list as well as the restricted-path flag: the flag
is a conservative quick check, not a complete safety analysis.

```
## release checklist

### Go to staging
- [ ] make a GitHub issue to track release with this checklist
- [ ] create release master branch
  - [ ] create a branch from upstream master named `zerotentwo` for release `v0.10.2`
  - [ ] revert risky commits (double check with autonomy team)
  - [ ] push the new branch
- [ ] push to staging:
  - [ ] make sure you are on the newly created release master branch (`zerotentwo`)
  - [ ] run `BRANCH=devel-staging tools/release/build_stripped.sh`. Jenkins will then automatically build staging on device, run `test_onroad` and update the staging branch
- [ ] bump version on master: `openpilot/common/version.h` and `RELEASES.md`
- [ ] post on Discord, tag `@release crew`

### Go to release
- [ ] before going to release, test the following:
  - [ ] update from previous release -> new release
  - [ ] update from new release -> previous release
  - [ ] fresh install with `openpilot-test.comma.ai`
  - [ ] drive on fresh install
  - [ ] no submodules; only the Chestnut big driving model uses LFS
  - [ ] check MTBF, etc.
  - [ ] stress test passes in production
- [ ] publish the blog post
- [ ] `git reset --hard origin/release-mici-staging`
- [ ] tag the release: `git tag v0.X.X <commit-hash> && git push origin v0.X.X`
- [ ] create GitHub release
- [ ] final test install on `openpilot.comma.ai`
- [ ] update factory provisioning
- [ ] close out milestone and issue
- [ ] post on Discord, X, etc.
```
