# QCOM B2 handoff — HOLD

Engineering source branch: `codex/mvl-qcom-b2-resource-pilot-20261107`; product source remains frozen `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`. Exact final checkpoint SHA and test counts are in the closing engineering response and test-results JSON. Ubuntu made no device connection or write. Do not publish this branch as an installable release.

Use [the gate report](QCOM_B2_GATE_REPORT_20261107.md), [the conditional protocol](QCOM_B2_PILOT_PROTOCOL_20261107.md), [test results](QCOM_B2_TEST_RESULTS_20261107.json), and [independent review](QCOM_B2_INDEPENDENT_REVIEW_20261107.md) together. The proposed script prints a read-only plan/inspection; `--execute` intentionally fails. The next work is a separately reviewed AGNOS 19.9 hard-quota and independent live-state watchdog design, then device read-only validation through the Windows authenticated controller. Any later source staging or one-warp compile is conditional on every hard gate; six captures, full product, package, device tests, installation, and release stay on HOLD. Preserve the known-good `/data/openpilot` and all historical B1 evidence.

If Ubuntu GitHub credentials are unavailable, the Windows authenticated helper may publish only the exact final branch SHA without force after checking remote ancestry. Publication does not change the NO-GO decision.
