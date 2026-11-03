# G05 offroad admission guard

Code commit: `e65dc8aa9053e53d41fb9a7c2f721b3e819557c6`. The new `starpilot_views/offroad.py` is a pure, renderer-neutral function. It accepts explicit UI state and a `BridgeSnapshot`, then admits optional status panels only when offroad HOME is visible, no update or alerts are present, and the snapshot does not contradict offroad state. Malformed flags or contradictory `device.started` / `selfdrive.active` fail closed. No native widget, IPC subscriber, service registration, control process or vehicle-facing code was changed.

The independent review found that the initial guard trusted `started=False` despite `snapshot.device.started=True`. Regression tests reproduced the disagreement; the guard now defers on both device-started and selfdrive-active evidence. Re-review found no remaining material defect in this host-only scope.

Exact-commit test result: 25 G05 tests passed; 389 combined offline host tests passed, 0 failed, 0 skipped. Native raylib startup test could not collect in the system Python because `capnp` is absent; using a read-only cached pycapnp archive exposed a second missing dependency, `opendbc`. No native UI startup or C3/C4 timing PASS is claimed.

The proposed native seam is an optional child of the large offroad `HomeLayoutSP`, subject to geometry and alert-priority proof. Mici needs separate work. Native UI gate remains **HOLD**.
