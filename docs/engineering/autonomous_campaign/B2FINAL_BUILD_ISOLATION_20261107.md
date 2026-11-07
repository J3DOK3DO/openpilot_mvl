# B2-Final build isolation — 2026-11-07

**Decision: HOST_DESIGN_PASS / DEVICE_EXECUTION_NO_GO.** `tools/release/qcom_b2final.py --execute` always exits 2 with `NO_GO_EXECUTION_DISABLED`; the earlier `qcom_b2_pilot.py --execute` lock is unchanged. Campaign 1 did not stage or compile on comma 4.

The only permitted future device run root is `/data/mvl-builds/4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb/pilot-<16 lowercase hex>`. A proposed run must place a separately verified Git checkout, Git metadata, compiler environment, `cache`, `tmp`, `home`, scratch, six outputs, logs and evidence inside that one root. It must never use `/data/openpilot`, installed caches or the 150 MiB device `/tmp`. The host test cleanup implementation rejects wrong run IDs, symlinks, unexpected mount IDs, owner/run mismatches and uncertain worker termination; it is restricted to `/tmp` fixtures and cannot clean a device.

The trusted source handoff has manifest SHA `998b417374930b75338b7ef8be9b3739d3e9e4d130c39ae0aa10e4abfcab9ee4` and tar SHA `37a82b744d079c0a130b3f88e24ba4d56b7aa5db4c0bc709449ed4f0ba3d60fe`. Both were rehashed in this campaign. The archive has no Git metadata; a separate exact 4b checkout is required for Git/submodule proof. The materialized frozen checkout passed prior source preflight and is not a build destination. No installed-path write or current device staging occurred.

Future build isolation requires independent proof that every process and writable path stays within the run boundary, a hard aggregate quota, bounded cgroup/process scope, authenticated continuous parked-state monitoring and a device-tested cleanup transaction. Host policy simulation cannot establish those properties on AGNOS. If any check is unavailable, the decision remains NO-GO.
