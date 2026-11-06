# Isolated QCOM build capacity

**Decision: REQUIRED_CAPACITY_UNKNOWN / HOLD.** The last read-only comma observation reported `/data` 8.83 GiB free, `/tmp` 150 MiB, `/dev/shm` 1.71 GiB free and MemAvailable 2.37 GiB. These are a snapshot, not current free space or peak build measurements. Installed `sp-honda-dev-202608` at `a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1` must remain unchanged.

| Term | Measured/known basis | Planning allocation |
| --- | --- | --- |
| Trusted source tar + selected extracted files | 223,006,720 + 219,518,275 = 442,524,995 bytes (422.0 MiB) | 0.5 GiB after metadata allowance |
| Host materialized exact-source checkout | 1009 MiB on this host, including hydrated selected assets/submodules | 1.25 GiB if replicated; do not also assume archive/extract copies are free |
| Python/compiler environment | 19.9 system rootfs includes venv; device default PATH lacked some tools | 0 to 1.0 GiB; route-specific, not measured on device |
| Isolated SCons cache | host one-library cache 6.7 MiB while running; default nominal prune target 2 GB | 0.25/2/3 GiB scenarios; pruning is not a peak bound |
| Six QCOM outputs + GPU scratch + TMPDIR | no measured Qualcomm peak | 1/2/4 GiB hypothetical only; **unknown** |
| Logs and evidence | unmeasured device run | 0.25 GiB planning |
| Free-space reserve | conservative engineering stop | 2 GiB minimum, 4 GiB preferred |

The values below are **scenarios, not measured requirements**. They account for a single source checkout (1.25 GiB), a 0.25 GiB log allowance and 2 GiB reserve. If a tar plus extracted copy is also retained, add at least 0.5 GiB. Full product staging adds further unknown space.

| Scenario | Environment | Cache | QCOM outputs/scratch/TMPDIR | Total including source, logs, 2 GiB reserve | Versus observed 8.83 GiB |
| --- | ---: | ---: | ---: | ---: | --- |
| Low | 0 | 0.25 | 1 | 4.75 GiB | Fits arithmetic only; unmeasured peak |
| Expected | 0.5 | 2 | 2 | 8.0 GiB | 0.83 GiB nominal margin, below a robust measured margin |
| Conservative | 1 | 3 | 4 | 11.5 GiB | Exceeds observation by 2.67 GiB |

No scenario establishes readiness because actual GPU compiler scratch, output size and thermal/RAM peaks are unknown. `/tmp` is too small for large compiler scratch. `/dev/shm` consumes shared RAM. The Ubuntu engineering volume had 24 GiB free after the verified image/rootfs and detached source were retained; no pinned source, backup or historical evidence was deleted. This host has no Qualcomm GPU.

**Conditional authorized sequence:** first remeasure device `/data`/RAM/CPU+GPU temperatures and installed SHA read-only; choose a single isolated `/data` workspace outside installed source/cache; preflight exact source and tools; place `TMPDIR` and `cache_dir` inside that workspace; start with `-j1`; monitor actual peak allocations and temperatures after each artifact; export hashes/logs before any cleanup. Stop before transfer/build if predicted peak plus 2 GiB reserve exceeds fresh free space. During build stop on free space below 2 GiB, OOM, GPU faults, unexpected thermal rise or missing actual GPU sensor, source/AGNOS mismatch, timeout, or any touch to installed paths. Do not delete known-good cache or user data for capacity.
