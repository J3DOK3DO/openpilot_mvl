# C9 final scoped source review and release HOLD — 2026-11-09

## Identity and device preflight
Reviewed executable source: 1616eb4ceb53576ce9b51e58785ab5e4d7d176ec. Frozen full-product source: 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb, AGNOS 19.9. The active installed Comma OpenPilot remained at 376c44b5731b2655e5c2f301b73c9729eb499e91.

The original C9 hand-built read-only kit omitted tools/release/preflight_readonly.py. The full frozen-source preflight initially returned HOLD for that missing kit helper, not a frozen-source defect. The coordinator restored the exact trusted helper (SHA256 c04d47fd2e07f8bac34c7c53b852e8b48d3367ed269999fed0eb7d9f358b3537). Subsequent real device validation returned PASS with zero issues, 7 pinned submodules, 286 hydrated LFS assets, zero dirty files. The B3 first-warp READ-ONLY dry run returned READ_ONLY_PREFLIGHT_PASS_EXECUTION_NOT_AUTHORIZED, process exit 2, no scratch, no model output and no active source change. Source evidence SHA256 1ab26219276ce5d3b6d123445003d63cdd51f8dc20b27fbb4f0dc99937f28a81. B3 dry-run evidence SHA256 9a7565feb7cd9f2930afdc08f4329ed7058394ab8f5d1bba649017519449868b.

## Independent Qwen review adjudication
Final Qwen code review at 1616 produced contradictory verdict text: FAIL_MATERIAL_SOURCE_DEFECT and PASS_SCOPED_WITH_PHYSICAL_HOLD, claiming omitted helpers, wrong preflight hash and missing tamper/symlink enforcement. Preserve its raw artifact outside Git as C9_QWEN_REVIEW_FINAL_1616.txt, SHA256 d0c096776d7cdc861e77a8833228f768363c97ee33bb85b87a8983a85d493307.

Source-backed checks refute the alleged omissions and wrong hash: c9_device_kit.FILES includes both agnos_image.py and preflight_readonly.py, with both actually present in the deterministic archive; the committed preflight sha256 equals the pinned value. A specific regression test proves omission of either helper or the pinned six-target plan is rejected. An independent coordinator reproduction created separate temporary Git repos and ran the actual packer (not a mock). Intact code: ACCEPTED as NOT INSTALLABLE. Five negative cases: missing agnos_image, missing preflight helper, tampered Python input, replaced symlink and a committed wrong preflight hash all REJECTED. Raw report C9_QWEN_FINDINGS_REPRODUCTION_20261109.json SHA256 36a212df0137273b2f9df12b36de2d3c51115234ed2090d23d8122e4bf9f6ac2.

Coordinator scoped offline verdict: ACCEPTED_WITH_EVIDENCED_LIMITATIONS. The independent Qwen opinions are preserved, not silently recast as an unqualified PASS. No full-product, physical or vehicle-safety approval is claimed.

## Actual stage outcomes
Additional native model-independent CDM ELF64 AArch64 shared library linked successfully; sha256 097a657c99e62b0c4797beba03f64d3e59fe72991050780bfe939b525ba6332b. This is not camerad or the complete product.
At the reviewed executable code commit 1616, 218 release tests ran with 209 PASS, 9 platform SKIP and 0 FAIL; 10/10 native and 4/4 recovery focused tests PASS. Both standalone B3 and combined R0 release admissions return exit 2. Latest source test logs, kit hashes, raw reviewer outputs and build artifacts are in /mnt/commadrive/MVL_C9_B3_G10_R0_ARTIFACTS_20261109/.

Mandatory status: genuine Qualcomm outputs 0/6, full AGNOS 19.9 G10 native product NOT_BUILT, Comma physical qualification 0/10, RC_NOT_INSTALLABLE / HOLD. Missing requirements include independent trusted physical stationary and ignition monitoring, sustained external power qualification, abort/recovery rehearsal, real Qualcomm execution provenance, product ABI/package closure, Panda firmware and protected rollback evidence.

The kit and R0 tar are engineering evidence only; no installation or GPU execution is authorized by this source. No CAN/Panda firmware, steering, braking, ACC, controls, protected Params, active installed software or road testing were modified or qualified. Publishing C9 is an engineering-source checkpoint only, NOT a production Comma clean-install release.
