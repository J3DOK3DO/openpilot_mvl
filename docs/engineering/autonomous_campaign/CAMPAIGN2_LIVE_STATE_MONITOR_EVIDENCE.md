# Campaign 2A live-state evidence

**Result: HOLD_LIVE_STATE_UNPROVEN.** A strict-host-key authenticated, read-only, five-second cereal subscription on 2026-11-07 ran for 5.056 seconds: `pandaStates=51`, `carState=0`, `controlsState=0`. Panda was last reported alive and ignition was never observed true. Zero car/controls updates means stationary and disengaged state were not observed; it does not imply either condition. This is a snapshot, not a 30-second preflight or a monitor during build.

`tools/release/campaign2_passive_telemetry.ps1` defaults to printing its plan. With `-RunReadOnly` it uses the existing authenticated Windows SSH alias, strict host-key checking, bounded `timeout`, and `PYTHONDONTWRITEBYTECODE`; a Python error or timeout now propagates a nonzero exit status. This repair was made after the saved observation, whose script hash identifies the earlier version. Both versions leave the gate unchanged.

A future independent monitor must prove at least 30 seconds of fresh concurrent ignition, speed/park or physically disconnected bench state, and engagement data, with sample gaps ≤1 second. During any separately authorized pilot it must fail closed for missing/stale data, ignition, motion, engagement, watchdog loss or supervisor failure. The host-only guardian has no vehicle-state adapter. No device monitor was installed or tested.
