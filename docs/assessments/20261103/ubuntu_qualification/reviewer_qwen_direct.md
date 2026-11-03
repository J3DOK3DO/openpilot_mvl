# Independent Qwen advisory and OpenCode execution record

**Campaign:** UQ-20261103
**Source:** Direct Windows Ollama `qwen3:8b`, CPU mode, using a written factual summary of the Ubuntu qualification findings.
**Result:** Response received; deployment HOLD.
**Limit:** This was an advisory review of supplied facts, **not** an independent source-code audit, validation of actual ECU hardware, or Qwen3-Coder 30B review.

## Exact reviewer response

> The evidence provided demonstrates that the MVL (protected controller) has passed 92 host tests on Ubuntu, and the Honda safety Python suite has passed 1046 tests with 612 skips, indicating partial validation. However, it does not prove functional safety compliance, real-world robustness, or that new features are safely integrated. The StarPilot:Dom is only a feature donor, not a safety controller, and no new features have been deployed.
>
> Additional verification gates should include: (1) dynamic testing of safety-critical paths under real-world conditions, (2) formal verification of FLM and Galaxy modules, (3) validation of IPC/msgq communication under fault scenarios, (4) safety certification of compiled libraries (libparams_c.so), and (5) integration testing with existing ACC/CMBS/AEB systems.
>
> Top hazards for a stock ACC/CMBS/AEB-preserving integration include: (1) false positive braking due to misinterpreted sensor data, (2) degraded CMBS performance from IPC interference, and (3) AEB override risks from FLM misreporting.
>
> This is **not approved for live vehicle deployment** due to insufficient evidence of safety compliance, lack of deployed features, and unverified dynamic behavior.

## Engineering interpretation

The Qwen reviewer appropriately declined deployment approval. Its suggested hazards are **hypotheses, not established failures in the pinned code**. In particular, the source checks do not establish that FLM can override AEB, that CMBS is degraded by IPC, or that the compiled Params library needs formal safety certification as an isolated component. Those claims must not be promoted to factual defects. Real vehicle system qualification involves owner and subsystem evidence, not an AI statement of certification.

The review prompt described an earlier 92-pass MVL subset and the 1,046-pass Honda safety tests. A **separate later** expanded result of 1,140 passed / 613 skipped exists against the newest MVL SHA; Qwen did not independently inspect that source or log. Do not use the Qwen reply as verification of the newer test run.

## OpenCode and Qwen3-Coder result

An assessment-specific Windows `opencode run --standalone --model ollama/qwen3:8b` invocation produced no output in its captured log and stalled. Its process was terminated without disturbing unrelated OpenCode sessions. The Windows RTX 4070 was under VRAM pressure; `qwen3-coder:30b` was installed but **not** used to produce a completed independent code review. The requested Codex Sol assessment also did not finish: a broader Sol attempt timed out. A **separate supported Codex model** completed an independent read-only source assessment, recorded in `evidence/codex_independent_final.md`.

**Final Qwen status:** ADVISORY COMPLETE; INDEPENDENT EXACT-CODE QWEN3-CODER 30B SIGNOFF PENDING; VEHICLE RELEASE HOLD.
