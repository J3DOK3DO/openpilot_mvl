# G09 — offline research simulation only

**Target context:** 2025 US Honda Accord 11G Hybrid, Bosch-C/CAN-FD. **Baseline:** `f19b4ea0dfd0f3e3ab2537dba2d0bfb863760ed0`. This is a synthetic, stdlib-only verdict engine. MVL remains the only possible vehicle-control owner; this package does not claim or create any authority.

The package evaluates seven concepts: AOL/MADS axis authority, lane/curvature confidence, FLM torque learning, SLC advisory speed source, curve speed, conditional experimental state, and Bosch-C LongControl stock authority. Its outputs are only `PASS_AS_RESEARCH`, `HOLD`, or `REJECT` plus explicit risk reasons. There are no control values, targets, CAN payloads, steering/brake requests, cruise outputs, subscriptions, publishing, Params writes, or production registration.

`PASS_AS_RESEARCH` means a complete **synthetic** case passed this classifier. It is not a vehicle, OEM, road, hardware, or release certification. Missing Honda identity/safety evidence, stale/invalid bridge evidence, driver override, EPS fault, FCW/AEB/CMBS conflict, stock ACC ownership, and disagreement all fail closed to `HOLD`; identity mismatch and `NO_C6_12_HISTORICAL_REUSE` are `REJECT`.

## Reproduce

Run from the repository root with Python 3.12:

```bash
python3.12 -m pytest -q openpilot/sunnypilot/starpilot_research/tests
python3.12 -m compileall -q openpilot/sunnypilot/starpilot_research
rg -n "sendcan|PubMaster|Params\.put|carcontroller|steer|brake|CAN" openpilot/sunnypilot/starpilot_research
```

The parameterized adverse matrix has 182 negative cases (26 adverse injections × 7 families), exceeding the requested 50. Every concept requires the complete synthetic confidence bundle, so a weak supporting channel cannot be ignored. Tests are local and deterministic; no real car traffic, network download, device, Panda, ECU/UDS, CAN, or AGNOS interaction occurs.
