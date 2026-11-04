# Optional passive Honda 11G health observation

These scripts are **supplemental diagnostics**, not comma 4 release acceptance tests or proof of Honda ACC, FCW, CMBS/AEB, braking or Panda safety. They are for manual use only after the user connects a comma 4 to a parked 2025 US Accord Hybrid. No script transmits CAN/UDS, queries ECU firmware, changes Params/Panda policy, starts controls, or requests a maneuver. The collector subscribes only to existing low-rate status topics for at most 15 seconds. It never subscribes to raw CAN, writes vehicle configuration, or includes VIN, location, route IDs or credentials in its report.

Run from the source root on the comma only after confirming the car is parked, stable power and device access. The script stops if `vEgo` exceeds 0.1 m/s or selfdrive reports enabled/active. If these fields are unavailable, it reports UNAVAILABLE rather than proving the car parked.

```sh
python3 -m tools.honda11g_health.collect_health --device --ack-parked --seconds 5 --output-dir /tmp/honda11g-health
python3 -m tools.honda11g_health.validate_report /tmp/honda11g-health/health.json
```

Review `/tmp/honda11g-health/health.json` and `health.md` locally before sharing. `PASS_OBSERVED` means a field was seen, not that a safety function was tested. `WARNING`, `UNAVAILABLE` and `NOT_TESTED` retain their literal meanings. Panda firmware hash remains UNAVAILABLE because no active query is issued. CAN-FD flags and receive/error counters come only from existing `pandaStates` messages; no CAN frame is sent. `stock_acc_qualification` and `oem_collision_mitigation` are always NOT_TESTED.

Offline fixture check, without messaging or a connected car:

```sh
python3 -m tools.honda11g_health.collect_health --fixture /path/to/fixture.json --output-dir /tmp/honda11g-health-fixture
python3 -m tools.honda11g_health.validate_report /tmp/honda11g-health-fixture/health.json
```

Stop and preserve the report if the device becomes unstable, the vehicle moves, or stock safety indicators are unexpected. Do not interpret this collector as permission to install or activate a candidate.
