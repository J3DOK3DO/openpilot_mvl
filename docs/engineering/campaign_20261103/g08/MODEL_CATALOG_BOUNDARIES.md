# G08 offline model catalog: boundaries and verification

This is an isolated, offline, read-only helper for a caller-supplied JSON
inventory. It is not registered with production startup, `modeld`,
`modeld_v2`, the MVL message bus, or the M0–M3 bridge. Importing and parsing
have no filesystem access. Verification reads only an explicitly selected file
below a caller-injected directory. It has no download, install, activation,
subprocess, Params, PubMaster, sendcan, Panda, ECU, UDS, CAN, or vehicle
control path. MVL remains the sole vehicle-control owner.

The implementation follows the M0–M3 bridge's pinned-MVL, read-only posture:
no new serialized schema, no generated schema changes, no shared Params, and
all behavior is off unless an external caller explicitly parses a catalog and
explicitly asks to inspect one selected file. This generic metadata utility
does not claim an Accord 11G permission, safety state, integration, or release.
It is offline engineering for the stated 2025 US Honda Accord 11G Hybrid
Bosch-C/CAN-FD context only and never certifies a vehicle release.

## Contract

The exact JSON shape is `{ "models": [ ... ] }`; each entry has exactly:
`id`, `name`, `version`, `sha256`, `size`, `target_abi`, and
`expected_runtimes`. Entries, IDs, strings, JSON bytes, entry count, runtime
count, and declared model size are bounded. IDs are unique. `target_abi` is
allowlisted to `x86_64` or `aarch64`; runtimes are allowlisted to
`onnxruntime`, `qnn`, `snpe`, or `tinygrad`. Parsed entries are frozen
dataclasses.

`verify_selected_file` rejects absolute/traversal paths, non-regular files,
and every symlink component. It uses `lstat`, requires the injected root itself
not to be a symlink, checks the declared size before reading, and hashes with a
64 KiB bounded stream. Any unknown, unsafe, unavailable, changed, mismatched,
or unsupported condition returns `HOLD`.

## Three deliberately separate claims

1. Digest validation is only an equality check: the selected ordinary file's
   byte count and SHA-256 equal caller-provided allowlisted metadata. `PASS`
   proves neither model behavior nor loadability.
2. ABI inference is intentionally absent. The declarative compatibility check
   compares only supplied strings (`x86_64`/`aarch64` and exact AGNOS
   `19.8.1`) with the metadata. A match reports
   `COMPATIBLE_METADATA_ONLY`, not an ABI attestation. Unknown inputs are
   `HOLD`.
3. Physical inference startup qualification would require separately running
   the real target's production inference stack with its runtime, drivers,
   memory, model format, and safety process. This code does none of that and
   cannot establish it—especially not from x86-64 host tests for AGNOS ARM64.

## Reproducible checks

Run from the repository root with the host Python 3.12 environment:

```sh
python3.12 -m pytest -q openpilot/sunnypilot/starpilot_models/tests
python3.12 -m compileall -q openpilot/sunnypilot/starpilot_models
```

PASS means only that the offline schema and read-only integrity checks passed.
HOLD is the required outcome for unknown platform information, invalid catalog
metadata, unsafe selections, symlinks, size/digest mismatch, or any I/O
uncertainty. Neither outcome activates a model or qualifies physical inference.

## Independent-review remediation

Codex identified a high-priority time-of-check/time-of-use gap: prior code validated path components using lstat, then reopened by path. Replaced it with a single openat-style directory-FD walk using O_NOFOLLOW, O_DIRECTORY, O_CLOEXEC and final fstat on the held file descriptor. No precheck/reopen gap remains in the modeled threat boundary. Added tests for intermediate and root symlinks; digest verification remains read-only and cannot activate a model.
