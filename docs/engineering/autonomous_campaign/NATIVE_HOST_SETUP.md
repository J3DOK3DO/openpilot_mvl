# Reproduce the isolated native host and G03 IPC checks

This setup exercises the x86 host renderer and local msgq only. It does not qualify C3/C4, AGNOS, Panda, Honda OEM behavior, or release. The tested source commit is `6ea2fc99792a0f1a27d5e977fb6171637c5136cc`; later campaign commits change documentation only.

From the root of an isolated checkout, use Python 3.12 and source `docs/engineering/autonomous_campaign/native_host_env.sh`. The script verifies the pinned opendbc and msgq Git SHAs and the matching host `libparams_c.so` hash before setting `PYTHONPATH` to cached pycapnp 2.1.0 and comma-deps-raylib 6.0.0.1.post106 archives. It changes no package installation or AGNOS reference. Missing archives or SHA mismatch are HOLD, not a test PASS.

The native import needs a temporary host library link inside the isolated checkout. Create it only if `openpilot/common/libparams_c.so` is absent; remove the link after the test. Do not commit the symlink.

```bash
source docs/engineering/autonomous_campaign/native_host_env.sh
ln -s /mnt/commadrive/MVL_NATIVE_LATEST_20261103/openpilot/common/libparams_c.so openpilot/common/libparams_c.so
python3.12 -m pytest -q -p no:cacheprovider openpilot/selfdrive/ui/tests/test_starpilot_native_status.py openpilot/sunnypilot/starpilot_bridge/tests openpilot/sunnypilot/starpilot_compat/tests openpilot/sunnypilot/starpilot_views/tests openpilot/sunnypilot/starpilot_galaxy/tests openpilot/sunnypilot/starpilot_models/tests openpilot/sunnypilot/starpilot_research/tests docs/engineering/campaign_20261103/g10/test_agnos_passive_check.py
python3.12 docs/engineering/autonomous_campaign/probe_g03_host_ipc.py
rm openpilot/common/libparams_c.so
```

The exact-commit outcome was 400 passed, 0 failed, 0 skipped, plus local capnp/msgq roundtrips for eight G03 schema paths. All 254 quarantined Params keys remain DENY. See `TEST_RESULTS.json`, `N1_NATIVE_HOST_EVIDENCE_20261103.json`, and `N2_ARM64_PREFLIGHT_20261103.json` for provenance and limits.
