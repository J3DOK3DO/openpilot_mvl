# G05 status — read-only StarPilot-inspired presentation prototype

## Result

**UI view-model: PASS (offline only).** `openpilot.sunnypilot.starpilot_views`
is a new, unregistered pure-Python M0–M3 presentation layer. M0 accepts the
existing pinned immutable `starpilot_bridge.models.BridgeSnapshot`; M1 rejects
malformed or stale accepted projections; M2 validates finite bounded geometry
and selects compact/full layout; M3 creates immutable renderer-neutral panels.

**C3/C4 raylib native render: HOLD.** No native renderer adapter was added.
Adding one requires changing or registering against MVL's native UI stack, which
is outside this isolated scope and has not received device/native-render proof.
There is no dynamic startup registration, UI-file change, vehicle control,
messaging publish, Params write, or native UI start.

## Safety and ownership boundary

This is a read-only display prototype for the 2025 US Honda Accord 11G Hybrid
Bosch-C/CAN-FD context only. MVL remains the sole vehicle-control owner. It
does not change Panda, CAN, ECU/UDS, opendbc, Honda controller, manager,
onroad UI, or driving control. It is not vehicle-release certification.

Critical alerts fail closed: generated content is empty and `defer_to_mvl=True`.
Every OEM/MVL high or critical alert is retained in `protected_alerts`; the
highest-priority alert is also the overlay. Alert input is read-only and its
priority is never downgraded.

## Reproduce

From the repository root, using host Python 3.12 and pytest:

```sh
python3.12 -m pytest -q openpilot/sunnypilot/starpilot_views/tests
```

Expected result: `12 passed`. This command is offline and does not start a
native UI.
