# Independent review ledger

The prior G03/G05/G06/G08/G09/G10 source reviews are retained under `../campaign_20261103/g*/INDEPENDENT_CODEX_REVIEW.md`. They do not certify native device behavior.

The G06 transport contract remains a design artifact; any adapter implementation requires independent security review before gate promotion. The latest exact-source review is recorded below.

## G05 read-only architecture assessment, 2026-11-03

Independent reviewer inspected exact source at `5d2d2cae47ff1548e317bacb1357fbb44b9d8388`. The native UI is Python raylib. `openpilot/selfdrive/ui/ui.py` selects the large or mici layout; `openpilot/selfdrive/ui/layouts/main.py` routes offroad HOME versus ONROAD. The least intrusive candidate is an opt-in read-only child of `HomeLayoutSP` on the large offroad HOME screen. Existing UPDATE and ALERTS routes in `openpilot/selfdrive/ui/sunnypilot/layouts/home.py` and offroad alert sorting in `openpilot/selfdrive/ui/widgets/offroad_alerts.py` retain precedence. The panel must disappear on started transition. Mici has a separate home layout requiring separate qualification. The existing G05 view model already defers optional panels for HIGH/CRITICAL OEM/MVL alerts, but no native widget registration or device timing evidence exists. Review verdict: source seam identified; native integration HOLD.

## G05 offroad guard independent code review

Initial verdict: FAIL, contradictory `device.started=True` and UI `started=False` admitted a panel. Remediation: defer on contradictory device-started or selfdrive-active evidence and reject malformed relevant fields; added adverse-state tests. Re-review verdict: PASS for host-only guard/test scope. Native caller timing, on-device alert precedence and renderer geometry remain HOLD.

## G03 pinned status crosswalk review

Initial verdict: NEEDS FIX. The verifier searched whole schema files and trusted aggregate Params counts. Remediation: verify direct declarations within uniquely named structs, confirm `CruiseState` is nested in `CarState`, and inspect all 254 Params entries for DENY/read-disabled/write-disabled. Re-review verdict: PASS for source-schema evidence. No IPC binding ABI or device runtime qualification is inferred.

## Final source and recovery boundary review

Independent reviewer confirmed the branch diff adds only the offline G05 guard and tests; no Honda/Panda/control/manager/native UI registration changes. It found a per-command lock gap and stale release/recovery prose. The lock was replaced by a persistent token lease with atomic claim/command/finish serialization, heartbeat, stale-token replacement and interrupted-run tests; recovery prose and test count were corrected. The current source boundary is acceptable for offline engineering review. This is not native UI, target, device, OEM safety or deployment approval.

## G10 continuation exact-source review, 2026-11-04

An independent agent inspected exact commit `162391f22567774166a6bd02024a65d969f63b59` against PR #1 head `b070247da792f216a558e250078caf62d201d97e`. Verdict: **PASS for narrow offline scope**. The source diff fixes only the G08 actual-NUL path guard and its regression. The committed G05 bench plan and G10 environment document retain full-product, device, Panda, Honda OEM, protected-recovery and deployment HOLD decisions. No control, Panda, Honda OEM, startup or live transport source changed. The reviewer ran 15 model catalog tests, all PASS, and confirmed no production `GalaxyHandler` registration or model runner. Later documentation evidence in the following checkpoint is outside this exact-source verdict; it records the 401-test and native ABI results separately. No actionable defect was reported.

Final docs-checkpoint review found a G06/G08 count mismatch: 38 was retained from the pre-fix run while the exact 162391f suite has 39. A clean exact-commit focused rerun passed 39/39; the evidence count and manifest hash were corrected before publication. The G10 document status was also updated from in-progress to completed representative library. The reviewer otherwise found source/recovery coherence and unchanged release HOLDs.
The reviewer also identified an outdated `source_of_truth` link to the historical 377-test report. Recovery now explicitly treats this autonomous-campaign directory as current and the older report as historical. The G06/G08 39-test focused count is recorded in a separate combined-test object, avoiding attribution to G06 alone.
