# M0–M3 implementation status and scope decision

**Vehicle:** 2025 US Honda Accord 11G Hybrid Bosch-C/CAN-FD. **Source:** MVL `sp-honda-dev-202608` @ `376c44b5731b2655e5c2f301b73c9729eb499e91`. **Engineering branch:** `accord11g-mvl-starpilot-readonly-integration-20261103`. This branch starts directly from the MVL upstream commit, not the earlier documentation branch.

| Milestone | State | Evidence |
|---|---|---|
| M0 fresh pinned MVL source and submodule | PASS | M0_SOURCE_AND_BOUNDARY_MANIFEST.json; Git HEAD and opendbc submodule |
| M0 pure MVL native host regressions | PASS for tested scope | M0_PINNED_MVL_NATIVE_BASELINE.log: 1,140 passed, 613 skipped, 1 warning, 1,190 passing subtests; exit 0 |
| M1 initial typed read-only status contract | IMPLEMENTED | SCHEMA_CONTRACT.md and immutable models; limited to 3 MVL topics |
| M1 254 shared literal Params names | QUARANTINED, NOT SEMANTICALLY RESOLVED | SHARED_PARAMS_QUARANTINE_254.csv: 254 keys denied for both read and write |
| M2 strict default-OFF feature registry | IMPLEMENTED | features.py, negative tests |
| M2 pure read-only, fail-closed topic adapter | IMPLEMENTED | adapter.py, immutable models, negative tests |
| M2 explicitly invoked SubMaster factory | IMPLEMENTED | factory.py, fake subscriber tests; no startup registration |
| M3 new bridge unit and negative tests | PASS for tested scope | M3_BRIDGE_HOST_FINAL.log: 51 passed, 0 skipped, 0 failed; exit 0 |
| M3 production OFF parity / release runtime | NOT HARDWARE VERIFIED | No process registration or protected source diff; exact device start/recovery is out of scope |
| Independent exact-diff source assessment | CODEX FINDINGS REMEDIATED; further review tracked | REVIEW_VERDICT.md |
| Comma install, Panda and physical Honda qualification | HOLD | No device install, CAN transmission, firmware or ECU diagnostic executed |

**Implementation surface** (new paths only): `openpilot/sunnypilot/starpilot_bridge/{__init__,features,models,adapter,factory}.py`; tests in `openpilot/sunnypilot/starpilot_bridge/tests/`; supporting docs and evidence under `docs/engineering/mvl_starpilot_m0m3/`. This is deliberately **not a StarPilot UI port**, **not a Galaxy service**, and **not a Honda driving-feature integration**.

**Runtime permission:** The module is dormant by design. Code can be imported by an explicit offline consumer and can display sanitized MVL status with deliberate opt-in; the new feature remains OFF in every existing MVL runtime because nothing calls it at startup. Passing tests do not make it installable or device-qualified.

**Safety and upstream rule:** The current stage may advance to separately reviewed M4 UI prototype engineering only after exact-source review and tests. No live driving functions, Panda/ECU updates, radar disable or custom longitudinal work is authorized by this package. For ARM64/AGNOS 19.8.1 runtime, physical Panda safety, OEM stock ACC/FCW/CMBS/AEB and any future live integration, see the separate mandatory Ubuntu qualification report and release hold.

**Reviewer provenance:** Codex was used as the initial implementer. Its long-running session stopped at the configured command timeout after generating the core implementation; the coordinator fixed the MVL-native import path and added separate subscriber-factory tests, then reran all 51. No unsupported automatic AI safety signoff is claimed.
