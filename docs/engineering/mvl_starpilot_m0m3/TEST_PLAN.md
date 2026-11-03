# M3 offline qualification, repeatability and negative-test matrix

## Reproducible commands and scope

New bridge test suite from the engineering root (pure Python, no hardware):

    PYTHONPATH="$PWD:$PWD/opendbc_repo" python3 -m pytest -q -ra openpilot/sunnypilot/starpilot_bridge/tests --disable-warnings

Pinned MVL native baseline was rerun in the separate pristine MVL source checkout `/mnt/commadrive/MVL_NATIVE_LATEST_20261103`, with verified HEAD `376c44b5731b2655e5c2f301b73c9729eb499e91`, using the existing isolated Python 3.12 native environment and native `opendbc`/IPC dependencies:

    PYTHONPATH="$PWD:$PWD/opendbc_repo:$PWD/msgq_repo" /mnt/commadrive/MVL_STARPILOT_UBUNTU_REASSESSMENT_20261103/.venv/bin/python -m pytest -q -ra \
      openpilot/sunnypilot/mads/tests openpilot/selfdrive/controls/tests \
      opendbc_repo/opendbc/car/honda/tests opendbc_repo/opendbc/safety/tests/test_honda.py \
      openpilot/common/tests/test_scons_cache.py --disable-warnings --maxfail=1

This latter suite is a **pristine baseline**, not proof of a merged runtime path. Source code outside the additive bridge remains unchanged in the engineering branch. Do not add overlapping earlier regression totals.

## Mandatory negative tests

| Case | Expected outcome |
|---|---|
| Empty registry / all OFF | No active topics, no native import/socket creation, no status-source read |
| Unknown feature key / non-boolean value / corrupted config | Configuration rejected, cannot enable feature |
| Explicit supported feature opt-in | Only associated allowlisted topic projected |
| Missing topic, no valid/alive or an exception | No corresponding status, typed rejection |
| Zero/negative/future/stale timestamp | Rejected; never displayed as current |
| Out-of-order timestamp or caller clock rollback | Rejected; no cached stale value forwarded |
| Invalid/missing bool, NaN, infinity, negative speed, invalid percentages or high temperature | Rejected, fail-closed |
| Raw source has VIN/fingerprint or other extra fields | Only allowlisted fields projected, no identity disclosed |
| Mutation attempt on snapshot/feature registry | Immutable or rejected |
| Bad settings/persisted Params | Not read: bridge has no Params runtime dependency |
| Privileged read/write or publication attempt | Static import/call scan and source diff must show no command path |
| Process crash/restart | Exceptions contained; no manager or controlsd dependency exists |
| Honda safety/stock ACC/AEB/CMBS | OUT OF SCOPE for this read-only unit test; remains physical HOLD |
| AGNOS/ARM64/Panda hardware and onroad UI | OUT OF SCOPE; distinct native/device qualification required |

The optional subscriber factory is separately tested with a fake native MVL `openpilot.cereal` module; no real SubMaster sockets are opened by the tests. Future device tests must verify actual service lifecycle, compatibility, performance, and urgent warning precedence. All future UI changes must re-run full bridge tests and the protected MVL native suite with exact source/firmware provenance and independently verified negative results.

## Hardening after independent review

Codex reproduced a FeatureRegistry subclass overriding active_topics and requesting unexpected sendcan subscription, and a clock call on the all-OFF path. Adapter and factory now require the exact registry type; disabled read returns empty snapshot before invoking clock. Three tests assert these properties. New exact-source suite: 51 passed, 0 skipped, 0 failed. This remains only host verification.
