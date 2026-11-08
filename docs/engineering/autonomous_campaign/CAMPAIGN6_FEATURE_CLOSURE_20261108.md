# Residual offline engineering closure matrix

| Area | New result | Disposition |
|---|---|---|
| C1 HOME status lifecycle | Invalid `started` values cannot trigger supplier read; regression added | PASS_SCOPED_HOST |
| C1 IPC concurrency | Concurrent call rejects immediately; timestamp state cannot rewind; deterministic regression | PASS_SCOPED_HOST |
| Honda warning priority | Prior accepted host fixtures retained; no warning/controller source changed | VERIFIED_NO_CHANGE |
| G06 / 254 Params | Production transport OFF and unregistered; protected keys DENY; source unchanged | VERIFIED_NO_CHANGE |
| StarPort | No approved non-actuating contract | EXCLUDED_PENDING_CONTRACT |
| C3 IPC native component | New AArch64 socketmaster static archive | BUILT_NOT_RUNTIME_TESTED |
| C5 backup | Hardlink/FIFO/path swap/duplicate/size rejection added | HOST_COPY_BYTES_ONLY |
| B3 Qualcomm | Owner exclusion, 0/6 authentic outputs | EXCLUDED_BY_OWNER |
| G10 product | Requires genuine B3 outputs | BLOCKED_DEPENDENCY |
| Physical Comma 4 | 0/10 | NOT_EXECUTED |

Remaining host-feasible work: independent review and final exact-commit regressions. Target-only acceptance requires genuine model outputs, full product, physical qualification and separate installation authorization.
