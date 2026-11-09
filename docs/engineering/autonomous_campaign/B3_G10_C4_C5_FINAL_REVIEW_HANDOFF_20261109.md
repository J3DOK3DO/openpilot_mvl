# Combined B3 / G10 / C4 / C5 — independent engineering handoff (2026-11-09)

## Exact engineering identity
- Repository: J3DOK3DO/openpilot_mvl
- Isolated branch: codex/mvl-b3-g10-combined-gated-20261109
- Base C3 checkpoint: 094540c7a085afd896583aa6f71845df9233213d
- Tested combined remediation source/evidence checkpoint: 3c6ec2af3c3d9564c5b8e0f84d20d168f4e25d6b
- Frozen full product source: 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb; AGNOS 19.9 frozen image SHA256 80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7.
- No protected vehicle-control, Panda firmware, CAN transmit, controller, stock ACC, protected Params or on-device files changed. No installation.

## New offline model-independent evidence
- VisionIPC C++ components compiled from the pinned frozen source in a network-disconnected bounded AGNOS AArch64 container into real archive libvisionipc.a. Four objects ELF64 AArch64; archive SHA256 25912c975eacb0164ea88fe0440b641776185be5a2e44978a5bd11caa8c652f4, genuine build exit 0. Never executed, not a full G10 SCons product.
- C3 prior native model-independent messaging ELF link evidence retained, not duplicated.
- B3 six authentic Qualcomm target outputs remain 0/6. A device internet/SSH connection is not sufficient to compile safely. Target device AGNOS19.9 aarch64 read-only source at a different installed commit, battery 66% discharging, about 9.57GB free on /data (only 0.98GB above static 8GiB reserve before staging), 2.5GB MemAvailable, independent live parked state unverified, hard quotas/thermal/error/abort missing. The manager was inactive in the passive snapshot; no active testing.

## Independent source review, remediation and verdict
- Qwen3-Coder 30B local Windows source-only review of the intermediate committed snapshot highlighted a genuine unsafe file trust class: precheck-then-open swap in Linux CLI and Get-FileHash vs Get-Content separate opens on Windows. Initial Qwen also asserted unsupported generic concerns (regex opens GPU, containerized AArch64 host compile touches device, all arithmetic capacity scenarios exceed available disk). These unverified assertions are not adopted.
- Codex implemented lstat+O_NOFOLLOW/O_NONBLOCK+fstat+same-fd bounded hash-and-parse Linux reader; held-handle reparse checks and same-buffer hash/parse Windows reader. Blocked CLI exit 2. New tests reject unsafe/special/symlink/oversized/swapped/malformed inputs, and cover actual BOM/CRLF evidence.
- Independent local Windows PowerShell verification of exact updated script SHA256 44e63f269c5acaa77d810d08683c0e8ecc36d9c34a2e334fe4fe365da54c9ea3: parse errors 0; saved pinned snapshot reports BLOCKED and process exit 2. No live device command executed by that test.
- Qwen second source-only re-review at immutable engineering checkpoint 3c6ec2af3c3d9564c5b8e0f84d20d168f4e25d6b reported PASS_SCOPED_SOURCE_REVIEW on snapshot trust remediation. Exact raw report retained outside Git at /mnt/commadrive/MVL_B3_G10_COMBINED_ARTIFACTS_20261109/QWEN_REMEDIATION_REVIEW_FINAL.txt with SHA256 cf0ea1b17202c7f309ad0a6b9dbdfeb6b64477c3be9589c0c218d556f3e4edf9. This is source review, not independent physical approval.
- Separate engineering coordinator reran final 196 release-tool tests: 187 passed + 9 platform skips + 0 failures; focused gate security 9/9, native 10/10, recovery 4/4. Actual device gate on pinned saved transcript returned exit 2 with AGNOS/arch PASS, installed source mismatch FAIL and external supply FAIL. Actual RC gate returned expected exit 2 / RC_NOT_INSTALLABLE. No install_allowed promotion.

## Mandatory remaining gates
1. B3: authentic Qualcomm compiler/device identity, independently verified sustained power and safe parked state, measured bounded per-target CPU/GPU memory/thermal/peak scratch with enforced 8GiB storage reserve, abort and recovery plus original six model outputs with independently authenticated native provenance. No execution authorized on present conditions.
2. G10: full cold native SCons product build using genuine B3 outputs and exact source/component ABI/package dependency closure, no dummy model products. Existing VisionIPC archive is limited component evidence.
3. C4/C5: protected recovery, actual Comma4 native runtime and offline parked acceptance followed by qualified physical fail-silent/stock ACC evidence. No installation or road testing based on this checkpoint.
4. Release remains RC_NOT_INSTALLABLE/HOLD, genuine B3 0/6, full G10 NOT_BUILT, physical Comma4 0/10; historic formal C3 still 2/4. Never infer physical safety from host tests or independent Qwen source verdict.

The campaign's published GitHub SHA and lease release are verified by the coordinator after publication; the engineering worktree must remain clean and release flags unchanged.
