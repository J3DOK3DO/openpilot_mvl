# G06 optional local transport contract

Status: **design accepted for offline analysis; implementation and deployment HOLD**. Source checkpoint: `5d2d2cae47ff1548e317bacb1357fbb44b9d8388`. This contract does not register or start a service.

## Ownership and isolation

- `GalaxyHandler` remains the only request evaluator. A future transport adapter must be a separate package with no imports into Honda control, Panda, modeld, manager startup, or onroad UI processes.
- Default state is OFF with no socket and no background thread. Failure to construct or serve the optional adapter must leave normal MVL startup unaffected.
- The snapshot provider is read-only, bounded, monotonic-time checked, and must not own a vehicle-control publisher or `Params.put` path. The adapter cannot turn a host-only PASS into a device PASS.

## Proposed local-only boundary

A Unix domain socket is the preferred candidate for offline prototyping, under a dedicated runtime directory with owner and group defined by an explicit device access policy. The final choice is **unapproved** until device users, filesystem permissions, cleanup behavior, and threat review are known. No TCP listener is authorized by this contract.

The adapter must check peer identity (not just a filesystem path), reject unauthorized peers before reading a request, and preserve the core token check. Its endpoint must have a bounded request count, request bytes, header bytes, body bytes, idle timeout, total timeout, and concurrent-client limit. A future implementation must document exact values and demonstrate resource limits under load.

Normalize one request into `GalaxyRequest` only after rejecting duplicate or ambiguous authentication headers, invalid encodings, malformed method/path, bodies on GET, and ambiguous framing. Never reuse a connection after a parsing error. Responses must copy only `GalaxyResponse` status, headers and body; errors must not include tokens, snapshots, stack traces, paths or process identity.

## Evidence required before promotion

1. Exact source diff proving no vehicle-control, Panda, OEM-safety, model activation, or startup registration changes.
2. Negative tests for peer authorization, duplicate headers, overlarge and slow requests, connection floods, truncated requests, wrong token, provider failure, stale snapshot, and shutdown cleanup.
3. Isolated host integration tests plus target resource and IPC timing measurements.
4. Independent security review of the actual adapter implementation and its package/configuration.
5. Physical device and protected-recovery qualification before deployment.

Until those are complete, `G06_TRANSPORT_HOLD` remains the gate decision. See `G06_TRANSPORT_READINESS.md` and the original `../campaign_20261103/g06/GALAXY_API_CORE.md`.
