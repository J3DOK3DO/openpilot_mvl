# Remaining proof boundaries — all features HOLD for vehicle use

Every family remains **HOLD for vehicle/OEM use**, regardless of an offline `PASS_AS_RESEARCH` result.

| Family | Required OEM / physical bench proof not performed |
|---|---|
| AOL/MADS axis authority | Honda authorization, driver takeover behavior, EPS fault response, controlled bench and track safety review |
| Lane + curvature confidence | Sensor/model error envelope, camera obstruction cases, replay correlation, controlled track proof |
| FLM torque learning | EPS torque limits, persistence/rollback safety, thermal and fault-injection bench work |
| SLC advisory speed source | Source provenance, map/sign disagreement handling, HMI review; no cruise ownership transfer |
| Curve speed | Vehicle dynamics, tire/load/weather bounds, longitudinal owner review, track validation |
| Conditional experimental state | Explicit UX gating, state-machine hazard analysis, fault/restart behavior |
| Bosch-C LongControl stock authority | OEM ACC/CMBS/FCW/AEB ownership analysis, CAN-FD bench observation, safety case and Honda approval |

Not performed: OEM approval; physical Accord, traffic, road/track, HIL/SIL, Panda, ECU/UDS, CAN capture/transmit, AGNOS deployment, or production manager integration. No report from this directory can certify a vehicle release.

## Independent review hardening
All safety, native-status and provenance flags require exact Python booleans in frozen dataclasses. The review found that unvalidated truthy/falsy values could otherwise create an incorrect research PASS; additional regression tests enforce exact types and expected fault reason semantics. These remain only synthetic research verdicts, never vehicle-control permission.
