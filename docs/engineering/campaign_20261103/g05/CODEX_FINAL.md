Implemented G05’s isolated read-only presentation prototype.

- New pure view-model package: [starpilot_views](/mnt/commadrive/MVL_CAMPAIGN_G03_G10_20261103/g05/openpilot/sunnypilot/starpilot_views)
- Uses the existing immutable pinned `BridgeSnapshot` schema only.
- M0–M3 validation, bounded layouts, immutable models, palettes, compact/full layouts, stale/malformed rejection, and deterministic fallback.
- OEM/MVL high/critical alerts are retained; critical alerts fail closed and defer to MVL.
- No renderer adapter, UI modification, startup registration, vehicle/control/messaging/Params changes, commit, or push.
- Status and native-render HOLD boundary: [STATUS.md](/mnt/commadrive/MVL_CAMPAIGN_G03_G10_20261103/g05/docs/engineering/campaign_20261103/g05/STATUS.md)

Verification passed:

```sh
python3.12 -m pytest -q openpilot/sunnypilot/starpilot_views/tests
# 12 passed
```

Verified base commit: `f19b4ea0dfd0f3e3ab2537dba2d0bfb863760ed0`.