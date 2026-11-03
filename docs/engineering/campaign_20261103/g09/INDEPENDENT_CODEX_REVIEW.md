Found one safety-semantics bug:

- `SafetyContext` and `NativeMvlStatus` do not validate their boolean fields. Truthy non-booleans can produce `PASS_AS_RESEARCH`—for example, `NativeMvlStatus(1, …)` and `SafetyContext(0, 0, 0, 0)` pass the evaluator’s truthiness checks. This conflicts with the fail-closed intent used by the bridge and leaves no failure reason for malformed synthetic status. See [engine.py](/mnt/commadrive/MVL_CAMPAIGN_G03_G10_20261103/g09/openpilot/sunnypilot/starpilot_research/engine.py:24) and [models.py](/mnt/commadrive/MVL_CAMPAIGN_G03_G10_20261103/g09/openpilot/sunnypilot/starpilot_research/models.py:63).

Test gap:

- The adverse-case matrix only checks for any non-pass verdict and any reason, not the expected reason or reject-vs-hold semantics. A regression that mislabels an EPS fault as stale, for example, would pass. See [test_engine.py](/mnt/commadrive/MVL_CAMPAIGN_G03_G10_20261103/g09/openpilot/sunnypilot/starpilot_research/tests/test_engine.py:60).

Verified no actuator output paths, no `MVL CarController` imports, and no vehicle-operation/release claim; `PASS_AS_RESEARCH` is explicitly scoped to synthetic research. I made no edits. The pytest run could not start because this read-only environment has no writable temporary directory.