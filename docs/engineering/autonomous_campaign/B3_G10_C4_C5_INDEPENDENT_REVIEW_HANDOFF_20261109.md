# Independent review handoff — gated combined campaign

Review this branch as offline engineering evidence only. Starting published C3 SHA: `094540c7a085afd896583aa6f71845df9233213d`. Frozen product source: `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`. Branch: `codex/mvl-b3-g10-combined-gated-20261109`. No push, lease change, protected-path edit, device write or vehicle action.

1. Verify `B3_G10_C4_C5_DEVICE_GATE_20261109.json` against the external passive transcript SHA-256 `21f732825d9d61580e44e7c33e67cd9f8f4904884e84e96f284641529f13740d`. The malformed offroad/ignition line, offline supply readings and installed SHA mismatch must block compilation.
2. Verify `B3_G10_C4_C5_B3_READINESS_20261109.json` against frozen six-target plan SHA-256 `6a493a0d9418f62310ee9a0f33d8e50ade4d5dc768cd54ec9c20ad45eaf3cd6e`. All six output hashes remain null. Owner state is resumed, not executed.
3. Inspect `G10_VISIONIPC_BUILD_20261109.sh`, ignored `.g10_stage/visionipc_build.log` and archive. Expected archive SHA-256 `25912c975eacb0164ea88fe0440b641776185be5a2e44978a5bd11caa8c652f4`; four AArch64 objects; exit 0; no binary execution. The first failed warning attempt's raw log was overwritten and must not be credited as preserved raw evidence.
4. Check frozen SCons edges and package inventory in `B3_G10_C4_C5_G10_SOURCE_GRAPH_20261109.json`. This is source inspection plus one component archive, not full cold traversal or complete product build. The C3 messaging ELF link proof remains separately scoped.
5. Re-run the recorded clean-HEAD test commands and release admission in `B3_G10_C4_C5_TESTS_20261109.json`. Expected release exit is 2 with `RC_NOT_INSTALLABLE`.
6. Preserve the independent Qwen raw verdict `FAIL_SOURCE_PROVEN_MATERIAL_DEFECT` and coordinator adjudication in `C3_NATIVE_CLOSURE_INDEPENDENT_REVIEW_20261109.md`; neither is overwritten by this handoff.

**Missing for promotion:** authenticated genuine Qualcomm 6/6 and resource/parked/power prerequisites; exact target GPU/driver ABI; full SCons cold product and packaging; device native runtime; recovery proof; ten physical checks. Protected 254 Params DENY, Galaxy OFF, StarPort excluded and stock ACC safeguards remain unchanged. Coordinator retains the campaign lease and controls publication.
