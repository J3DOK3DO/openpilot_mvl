# Independent review ledger

The prior G03/G05/G06/G08/G09/G10 source reviews are retained under `../campaign_20261103/g*/INDEPENDENT_CODEX_REVIEW.md`. They do not certify native device behavior.

Current background branch: no new material source implementation has yet been submitted for independent review. The G06 transport contract is a design artifact; any adapter implementation requires independent security review before gate promotion.

## G05 read-only architecture assessment, 2026-11-03

Independent reviewer inspected exact source at `5d2d2cae47ff1548e317bacb1357fbb44b9d8388`. The native UI is Python raylib. `openpilot/selfdrive/ui/ui.py` selects the large or mici layout; `openpilot/selfdrive/ui/layouts/main.py` routes offroad HOME versus ONROAD. The least intrusive candidate is an opt-in read-only child of `HomeLayoutSP` on the large offroad HOME screen. Existing UPDATE and ALERTS routes in `openpilot/selfdrive/ui/sunnypilot/layouts/home.py` and offroad alert sorting in `openpilot/selfdrive/ui/widgets/offroad_alerts.py` retain precedence. The panel must disappear on started transition. Mici has a separate home layout requiring separate qualification. The existing G05 view model already defers optional panels for HIGH/CRITICAL OEM/MVL alerts, but no native widget registration or device timing evidence exists. Review verdict: source seam identified; native integration HOLD.

## G05 offroad guard independent code review

Initial verdict: FAIL, contradictory `device.started=True` and UI `started=False` admitted a panel. Remediation: defer on contradictory device-started or selfdrive-active evidence and reject malformed relevant fields; added adverse-state tests. Re-review verdict: PASS for host-only guard/test scope. Native caller timing, on-device alert precedence and renderer geometry remain HOLD.

## G03 pinned status crosswalk review

Initial verdict: NEEDS FIX. The verifier searched whole schema files and trusted aggregate Params counts. Remediation: verify direct declarations within uniquely named structs, confirm `CruiseState` is nested in `CarState`, and inspect all 254 Params entries for DENY/read-disabled/write-disabled. Re-review verdict: PASS for source-schema evidence. No IPC binding ABI or device runtime qualification is inferred.
