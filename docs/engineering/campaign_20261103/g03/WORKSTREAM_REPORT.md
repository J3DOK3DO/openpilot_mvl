# G03: MVL / StarPilot semantic crosswalk tool

## Status: HOLD — 254 keys retained in quarantine

This workstream adds an offline, stdlib-only evidence tool at
`openpilot/sunnypilot/starpilot_compat/`. It does not register a service,
read/write Params, publish IPC, or control a vehicle. MVL remains the only
vehicle-control owner.

The authoritative, exact unresolved-key list is the unchanged 254-row
[`SHARED_PARAMS_QUARANTINE_254.csv`](../../mvl_starpilot_m0m3/SHARED_PARAMS_QUARANTINE_254.csv).
Every listed key remains `DENY`, `ReadEnabled=FALSE`, `WriteEnabled=FALSE`,
`UNVERIFIED`, and `REQUIRES_EXACT_SCHEMA_SEMANTIC_REVIEW`. There are zero
approvals and no allowlist. A literal match, local occurrence count, or a
native MVL Params declaration is evidence only; it is never a type, owner,
default, authorization, lifetime, or migration equivalence proof.

## Tool contract

`render` validates the input's exact columns, 254 unique safe identifiers and
deny contract, then emits key-sorted stable JSON or CSV. It enriches a record
with a native `params_keys.h` declaration when locally present, while setting
the policy `METADATA_ONLY; all native Params reads/writes rejected`.

The classification is deliberately a review queue, not an approval:

- `SENSITIVE_OR_HIGH_RISK`: case-insensitive lexical signal for vehicle/control
  (`honda`, `car`, `control`, `steer`, `longitudinal`, `lateral`,
  `calibration`, `torque`, `safety`, `panda`, `can`, `ecu`, `firmware`,
  `enabled`, `engaged`, `decel`, `cruise`, `actuation`); credential/identity or
  privacy (`token`, `ssh`, `password`, `auth`, `access`, `vin`, `dongle`,
  `gps`, `location`, `route`, `camera`, `model`, `driver`, `dm`); or lifecycle
  (`boot`, `shutdown`, `reboot`, `uninstall`, `update`, `manager`, `pid`).
- `LOW_RISK_CANDIDATE`: none of those lexical signals. This only prioritizes
  human review; it remains denied until the per-key acceptance criterion in
  the quarantine CSV has been completed separately.

`inspect` accepts only a known, identifier-shaped quarantined key, traverses a
provided local MVL directory without a shell, ignores `.git`, and reports text
occurrences. Arbitrary patterns and paths such as `../key` are rejected.

## Source-backed ABI boundary

See [FIELD_INVENTORY.md](FIELD_INVENTORY.md). The inventory tool extracts only
direct Cap'n Proto fields and ordinals from local source. It explicitly rejects
`carState` field/ABI mapping because the pinned `opendbc_repo/opendbc/car/car.capnp`
is absent in this checkout. It does not infer Cython/nanobind compatibility.

## Reproducible checks

Run from repository root:

```bash
python3 -m pytest openpilot/sunnypilot/starpilot_compat/tests/test_crosswalk.py -q
python3 -m openpilot.sunnypilot.starpilot_compat --quarantine docs/engineering/mvl_starpilot_m0m3/SHARED_PARAMS_QUARANTINE_254.csv --params-keys openpilot/common/params_keys.h render --format json
python3 -m openpilot.sunnypilot.starpilot_compat --quarantine docs/engineering/mvl_starpilot_m0m3/SHARED_PARAMS_QUARANTINE_254.csv inventory --repository-root .
python3 -m openpilot.sunnypilot.starpilot_compat --quarantine docs/engineering/mvl_starpilot_m0m3/SHARED_PARAMS_QUARANTINE_254.csv inspect --mvl-root . --key AccessToken
```

PASS means source validation and offline evidence generation passed. HOLD
remains for every migration decision, vehicle release, AGNOS runtime claim,
Honda Accord qualification, CAN/UDS/ECU/Panda activity, or StarPilot driving
control change. None was attempted here.

## Independent-review correction: source provenance

An unverified caller-supplied params file is NOT an attested MVL source. Candidate metadata is now named `local_params_candidate_unattested` with `source_attested=false`; message inventory uses `LOCAL_SOURCE_UNATTESTED` and never claims exact Git provenance from a path alone. A future exact-SHA source attestation must be a separate gate. All 254 entries remain DENY.
