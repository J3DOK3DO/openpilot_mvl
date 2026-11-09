# Campaign 10 — B3 offline interlock hardening (2026-11-09)

## Provenance and boundaries

This source-only change starts from published Campaign 9 commit `815a8568762b5e4805f284aa218fbded179c69a8`. The product source remains frozen at `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb` (AGNOS 19.9); the pilot is a separate engineering utility, not a release or approved compilation procedure.

**Explicit HOLD:** Qualcomm captures 0/6, complete G10 product NOT_BUILT, physical C4 acceptance 0/10, R0 `RC_NOT_INSTALLABLE`. No active Comma installation, vehicle controls, Panda firmware, protected Params, ignition, or CAN transmissions were changed. No device contact, GPU compilation, road test or independent physical monitoring is claimed by this campaign.

## Changes

1. The B3 pilot checks that the log is a fresh direct child of its isolated scratch before reading the execution gate or creating scratch directories. Relative paths, traversal, existing files, symlinks, active checkout paths and out-of-scratch paths fail closed. The Windows launch wrapper applies the same direct-child requirement.
2. In `--execute` mode, exceptions can occur after some device writes. The CLI therefore reports `device_write_performed=null` and `write_state=UNKNOWN_REQUIRES_DEVICE_REVIEW`, rather than the unsupported former `false`. All failures stay `HOLD`, exit code 2 and `install_allowed=false`. Read-only exceptions retain `device_write_performed=false` and `write_state=NOT_ATTEMPTED`.
3. Python `-B` and `PYTHONDONTWRITEBYTECODE=1` reduce incidental bytecode writes during read-only preflight. They do not prove the absence of all writes by arbitrary helper programs.
4. New focused offline unit tests cover rejected log locations, log overwrite/symlinks, pre-gate rejection, error reporting, monitor field failures and Windows wrapper policy. Existing C9 hard-quota fixtures now use the newly required scratch-contained log location.

## Validation and release rule

Run from the committed engineering checkout with `PYTHONDONTWRITEBYTECODE=1`:

```bash
python3 -m unittest discover -s tools/release/tests -p 'test_*.py' -q
python3 -m unittest tools.release.tests.test_inspect_native_product tools.release.tests.test_campaign2_native_abi -q
python3 -m unittest docs.engineering.autonomous_campaign.test_campaignctl -q
python3 -m tools.release.combined_rc_readiness
python3 -m tools.release.qcom_b3_admission --plan docs/engineering/autonomous_campaign/B3C_SIX_TARGET_VERIFIED_PLAN_20261107.json
```

The last two admission commands must return HOLD (exit 2). Tests that inspect Git clean-state must be run **after** committing the engineering branch; running against dirty source is an expected fixture rejection. Do not infer execution permission from passing host regression tests or from a successfully generated kit. The physical monitor, sustained power, abort/recovery, actual Qualcomm execution evidence and independent provenance remain separate prerequisites.

The former C9 checkpoint and archived deliverables must remain unchanged. No installation-ready artifact can be published from this campaign; any GitHub publication is an engineering-source checkpoint only.
