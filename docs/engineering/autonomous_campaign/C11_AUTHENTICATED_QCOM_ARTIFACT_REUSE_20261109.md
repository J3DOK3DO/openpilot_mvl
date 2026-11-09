# Campaign 11 — signed Qualcomm artifact reuse route (2026-11-09)

## Decision and scope

**Reuse is conditionally permitted as an engineering evidence route, not as automatic B3 acceptance.** A reused Qualcomm model must be one of exactly six named artifacts from the frozen MVL model recipe. The source commit *may differ* only when the independently established build-relevant source dependency graph is byte-for-byte equivalent to the frozen version. The frozen MVL reference is source `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`, Tinygrad `92b742f711c7d216fd3ed7a46a30a959e3c43bd4`, AGNOS 19.9 and pinned image SHA-256 `80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7`.

The pinned conservative dependency graph has **513 files**, with a canonical SHA-256 digest `010f2eaf6474c1e7cd7193cf9c57921a552d660bb28d98c423ea7d3027440b9b`. The exact ONNX, compiler recipe, environment flags and QCOM backend must also match. Unlike a simple same-filename or same-ONNX check, this prevents model substitution across different compiler graph versions.

## Newly implemented offline qualification

`tools/release/qcom_b3_reuse.py` checks candidate file names, rejects malformed/foreign QCOM pickle structure **without loading or unpickling**, hashes each artifact, checks the exact committed source policy and strictly limits a potential reuse dossier to:

- All six exact model outputs with SHA-256 and size, no extra files and no symlinks.
- Complete signed producer capture record and separately signed independent review record, using distinct preapproved Ed25519 public keys pinned in the committed policy.
- Signed source/AGNOS/Tinygrad/ONNX/recipe/backend/Comma 4 identity and a complete matching 513-file compiler input graph.
- Per-artifact original compiler log, live device monitoring log, abort/recovery record and native inference trace, each hashed and bound to the signed dossier.
- Independent reviewer attestation of source equivalence, genuine Qualcomm compilation, target runtime/ABI, all six model inference checks and monitored abort/power/thermal behavior.

The trust registry in `B3_SIGNED_REUSE_POLICY_20261109.json` intentionally contains **no approved keys**. It must not be populated with arbitrary self-generated keys: independent ownership and key enrollment require a separate review of the real producer/reviewer identities and the underlying execution evidence. Signatures authenticate who signed a claim, not whether the physical claim is true; this requires independent corroboration.

Even if the complete dossier passes, the tool reports `ELIGIBLE_FOR_SEPARATE_B3_REUSE_ACCEPTANCE`, keeps `b3_verified_artifact_count=0`, `install_allowed=false`, and exits 2. Integrating an independently approved reuse decision into B3/R0 would be a separately reviewed policy change. **No existing B3/QCOM release gate is weakened.**

## Actual legacy inventory — preliminary disposition

A read-only search of Ubuntu and Windows backups found historical captures. The strongest candidate is the 2026-11-01 Track A/B package at:

`/mnt/commadrive/DOM7_V4_AUTOMATED_20261030/work/dom7-v4-trackab-native-build-20261101/.cache/qcom-artifact-package/artifacts/`

Five expected filenames have structurally plausible Qualcomm capture bytes and match the historical manifest's SHA-256, but **the main `driving_tinygrad.pkl` is missing**. The producer source commit is `4e3605e6747477153a025caab671c7d70f68fcc6`, not the frozen MVL commit. Of the frozen 513-file dependency graph, only 356 hashes match the historical manifest, 130 common paths changed and 27 frozen paths are absent from that manifest. The historical manifest also does not supply independently authenticated Qualcomm execution and target compatibility attestations. Therefore all five are **quarantined candidates**, none are accepted or copied into the frozen product. In particular, legacy StarPilot files and `big_driving_tinygrad.pkl` are not interchangeable with the required `driving_tinygrad.pkl`.

Saved offline evidence is in `/mnt/commadrive/MVL_C11_QCOM_REUSE_ARTIFACTS_20261109/`. No active Comma source, firmware, controls, CAN/ACC, protected Params or device files were touched.

## Recommended next sequence

1. Preserve the five historical candidates and provenance in read-only archive form; do not rename or substitute.
2. Search for a complete six-file package from the exact frozen model graph and obtain real producer evidence, independent reviewer attestation and approved trust identities.
3. If a genuinely equivalent complete package is discovered, perform the new offline signed qualification and a separate B3 admission design/review before any use.
4. If not, retain B3 at 0/6 and pursue the already-prepared first-warp native compilation only after independently verified physical isolation, sustained power, thermal monitoring and abort rehearsal. Then compile the remaining targets under separate bounded controls.
5. Do not start a G10 full cold build, device installation or vehicle test on the basis of this candidate review.

The reuse path cannot waive model provenance, physical monitoring or independent target verification.
