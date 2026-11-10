# C17 Comma 4 device preflight — HOLD template

Status: **NOT_RUN / PHYSICAL HOLD**. This is an acceptance record, not an installer. Nothing in the C17 host-bench archive may be copied to a device. SSH reachability, a hostname, or a LAN address is not identity or isolation evidence.

## Mandatory gate

Every item below must be completed for one uniquely identified physical Comma 4, reviewed by an independent witness, and approved in a separate device-specific record. A blank, inferred, remotely observed, or self-generated item is a failure. The gate is atomic: any non-PASS outcome keeps deployment prohibited.

| ID | Required evidence | Current outcome |
|---|---|---|
| P1 | Time-stamped photographs and witness signature showing the unit physically disconnected from vehicle harness, Panda, CAN, ECU, and ignition | NOT_RUN |
| P2 | Exact device serial, hardware revision, boot-chain identity, and AGNOS version captured from that physical unit and matched to the approval record | NOT_RUN |
| P3 | Measured isolated bench supply limits, current limit, temperature limits, shutdown criteria, and responsible operator | NOT_RUN |
| P4 | Complete off-device restoration backup manifest, per-file SHA-256, byte counts, acquisition method, storage location, and independent verification | NOT_RUN |
| P5 | Real restore rehearsal to an approved recovery target, with post-restore identity/hash evidence; a plan or archive listing is not a rehearsal | NOT_RUN |
| P6 | Independent reviewer signs the isolation, identity, power/thermal, backup, and restore evidence | NOT_RUN |
| P7 | Named authority signs a separate approval scoped to the exact serial, exact candidate SHA-256, time window, and rollback owner | NOT_RUN |

Machine decision rule:

```text
device_gate_pass = all(P1..P7 == PASS) AND all evidence hashes resolve off-device
install_allowed = device_gate_pass AND candidate_is_separately_reviewed
```

Current machine decision: `device_gate_pass=false`, `install_allowed=false`.

## Read-only identity session (future, separately approved)

Only after P1, the operator may conduct a witnessed, local, read-only identity session. The session must not scan a LAN, alter `/data`, `/data/openpilot`, `/dev`, sysfs, Params, boot slots, firmware, Panda, or services. Record the exact transport and all command output. Stop if the identity differs from P2 or any vehicle connection is observed. This campaign does not authorize or automate that session.

Minimum record fields:

```json
{
  "device_serial": null,
  "hardware_revision": null,
  "agnos_version": null,
  "boot_identity": null,
  "isolation_witness": null,
  "isolation_evidence_sha256": null,
  "supply_voltage_v": null,
  "current_limit_a": null,
  "temperature_c": null,
  "captured_at_utc": null
}
```

## Physical graphics acceptance (future)

With P1–P7 passed, separately reviewed device-specific tooling must demonstrate the authentic AGNOS compositor/backend and Adreno/display path on the identified unit. Required evidence includes process identity, ELF hashes, renderer/vendor/version, display mode, timestamped physical display capture, bounded start/stop status, thermal/power readings, and proof that no manager, controls, Panda, CAN, model, radar, planning, or vehicle service ran. Host Xvfb, Mesa, QEMU, emulated EGL, and screenshots copied from another system do not satisfy this gate.

## Rollback rehearsal (future)

1. Verify the off-device backup manifest and every SHA-256 before any candidate action.
2. Prove recovery media and procedure apply to the exact P2 identity.
3. Rehearse restore on an approved recovery target under the named rollback owner.
4. Re-capture identity and hashes after restore and compare them with P4.
5. Record elapsed time, failures, power/thermal behavior, and reviewer signature.
6. Keep the candidate prohibited until the real restore evidence is independently accepted.

No C17 artifact is a deployer, rollback image, firmware package, or permission to touch a device.
