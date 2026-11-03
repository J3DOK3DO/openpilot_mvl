# Accord 11G MVL-first — G03/G05/G06/G08/G09/G10 offline parallel engineering report

**Campaign:** 3 November 2026; 2025 US Honda Accord 11th Gen Hybrid Bosch-C/CAN-FD, exact target HONDA_ACCORD_11G. **Repository:** `J3DOK3DO/openpilot_mvl`. **Engineering base:** prior reviewed default-OFF read-only MVL bridge `f19b4ea0dfd0f3e3ab2537dba2d0bfb863760ed0`. **Original MVL upstream source:** `376c44b5731b2655e5c2f301b73c9729eb499e91`. **Source ownership:** MVL controls, MADS, OEM stock ACC and existing Panda remain unchanged. No StarPilot driving or system runtime source is mass imported.

## Gate disposition — distinction between host milestones and actual release readiness

| Gate | This campaign's actual deliverable | Evidence | Scope decision |
|---|---|---|---|
| G03 | Source-local literal crosswalk for **254 overlapping keys**, all `DENY`; two message inventories including a separately pinned native MVL source copy, identifying 34 deviceState, 12 selfdriveState and 52 carState fields | 7 passed / 0 skipped; G03_254_PARAMETER_EVIDENCE.json; G03_PINNED_SOURCE_PROVENANCE.json | **OFFLINE TOOL PASS, semantic migration HOLD**. No key auto-approved and caller file metadata is never considered source-attested by the CLI. |
| G05 | Renderer-neutral, immutable status view-model prototype, compact/full layout and themes, conservative data freshness and alert precedence | 13 passed / 0 skipped | **HOST VIEW-MODEL PASS, native MVL raylib/comma UI HOLD**. High/critical OEM/MVL alerts suppress optional panels. No native render or UI startup change. |
| G06 | Explicitly invoked, authenticated GET-only status/health/model-placeholder Galaxy handler, default-OFF, with no listening network server | 22 passed / 0 skipped | **HOST API CORE PASS, actual network/auth transport and device resource security HOLD**. No mutation endpoints or data export enabled. |
| G08 | Bounded model-inventory parser, immutable catalog, explicit read-only file SHA-256/size check and metadata-only target compatibility | 14 passed / 0 skipped | **HOST CATALOG PASS, modeld/JetLink runner and AGNOS execution HOLD**. No downloads, model writes, activation or inference. |
| G09 | Typed read-only **seven-family research** evaluator for AOL/MADS, lateral confidence, FLM, SLC advisory, curve speed, conditional mode and stock Bosch-C long authority; reason-only output | 261 passed / 0 skipped | **SYNTHETIC OFFLINE RESEARCH PASS, active car control HOLD**. Does not emit a steering/brake/cruise target or CAN message. No C6-12/C7 historical qualification is reused. |
| G10 | Read-only AGNOS 19.8.1 image inspection, reproducible hash/ELF ABI/disk/toolchain audit and target-build qualification plan | 9 passed / 0 skipped | **PASSIVE PREPARATION PASS, full AArch64 build/AGNOS boot/physical device HOLD**. |

**Integrated test result:** `CONSOLIDATED_HOST_REGRESSION.log` shows **377 passed, 0 failed, 0 skipped** in the consolidated source checkout: **51 retained M0–M3 bridge tests + 326 new tests** across G03/G05/G06/G08/G09/G10. Python compileall passed on all modules. This is a pure host/offline campaign; it does not count pre-existing MVL safety tests as new unique passes.

**Previously captured pinned native MVL host baseline:** 1,140 passed, 613 skipped, 1 warning, 1,190 passing subtests. That was measured on the original pinned MVL host source and is **not** a full physical Panda or device result and was **not re-executed on this consolidation checkout**. All new code remains in isolated, non-registered packages and documentation; the combined diff contains **zero existing vehicle-facing module changes**.

## Review findings and remediation

Codex was used for isolated implementation and independent read-only audits. Reviewers identified concrete, corrected issues. G03 originally called caller-supplied metadata a native source assertion; it now emits explicit `source_attested=false` and `LOCAL_SOURCE_UNATTESTED`. G05 was hardened so any OEM/MVL HIGH or CRITICAL warning defers the optional panels entirely. G06 default disabled settings now work without requiring a configured token (enabling still demands a token). G08 was corrected from a nonexistent `hashlib.compare_digest` to `hmac.compare_digest`, and replaced vulnerable path check/reopen logic with an O_NOFOLLOW directory-descriptor walk to prevent symlink-swap TOCTOU. G09 exact-booleans and fault-specific reason tests now prevent truthy/falsy synthetic evidence from incorrectly yielding research PASS.

Some independent Codex sessions could not run pytest in their read-only sandbox, so their conclusions are **source reviews**, not native execution certificates. The coordinator separately reran all tests on Ubuntu and retained exact output. Windows OpenCode/Qwen3 8B inference yielded no substantive response (output length exhausted). A separate direct Qwen2.5-Coder 14B source advisory completed and did not establish an additional code defect; this is *not* a complete security or Honda safety certification, and the raw model responses are retained.

## G10 exact passive evidence

- Image: `/home/jdkd/AGNOS_20261014/agnos_system.ext4.img`; read-only `debugfs` reports root VERSION **19.8.1**, issue **Ubuntu 24.04.5 LTS**.
- Image SHA-256: `98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8`.
- MVL native host `libparams_c.so` and `ipc_pyx.so`: **x86-64**, not AArch64.
- Missing standard `aarch64-linux-gnu-gcc` and `aarch64-linux-gnu-g++` on Ubuntu PATH; engineering data volume had approximately **7.6 GiB** free during campaign.
- No complete cold ARM64 build, device boot, Panda hardware check or protected rollback exercise was run. The image VERSION is not evidence of the current comma firmware.

## Not authorized by these results

These results do not authorize an installable combined branch, device activation, OEM radar disable, ECU diagnostics, custom Bosch-C longitudinal, Panda firmware/safety changes, steering/ACC commands or live AOL/Lane/FLM/SLC integrations. The earlier failed Dom AOL engagement, which left stock ACC functioning during that observation, cannot prove safe OEM stock-ACC takeover or FCW/CMBS/AEB preservation across all faults and modes.

The next release-facing gates remain **native C3/C4 UI rendering, isolated security and hardware bench, full AArch64 AGNOS target build, physical Panda safety, Honda OEM collision-mitigation validation, exact-commit integrated review, and protected rollback**. Until then, **vehicle release HOLD**.

## Reproducible host qualification

```sh
PYTHONPATH="$PWD:$PWD/docs/engineering/campaign_20261103/g10" python3 -m pytest -q -ra \
  openpilot/sunnypilot/starpilot_bridge/tests \
  openpilot/sunnypilot/starpilot_compat/tests \
  openpilot/sunnypilot/starpilot_views/tests \
  openpilot/sunnypilot/starpilot_galaxy/tests \
  openpilot/sunnypilot/starpilot_models/tests \
  openpilot/sunnypilot/starpilot_research/tests \
  docs/engineering/campaign_20261103/g10/test_agnos_passive_check.py
```

The consolidated engineering branch aggregates only the six independently committed isolated branches atop M0–M3. Every individual gate retains its own `GATE_FINAL_STATUS.md`, `FINAL_HOST_TESTS.log`, `GATE_EVIDENCE_MANIFEST.json`, implementation and reviewer artifacts. This is intended for review, future safe feature-specific porting and reproducible offline assessment, **not** for installation on the comma.
