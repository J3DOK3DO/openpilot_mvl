# G10 stock model artifact preflight

Status: offline validator implemented; MVL QCOM model package remains **HOLD**. A static PASS is not model execution, physical comma 4 qualification, or deployment approval.

`tools/release/mvl_model_artifacts.py` records and verifies a local manifest for the exact MVL source commit, the pinned `tinygrad_repo` Git link, tracked model build recipe and compiler source bytes, AGNOS 19.8.1 reference image hash, both ONNX LFS identities, and all six stock QCOM model/warp outputs required by MVL `openpilot/selfdrive/modeld/SConscript`. It refuses changed tracked compiler files, untracked compiler source, missing/extra artifacts, symlinks, duplicate manifest keys, CPU/LLVM captures, foreign GPU captures, malformed pickle opcode streams, and hash/size mismatches. It only parses pickle opcodes; it never unpickles or runs a model.

After producing all six outputs on a trusted matching Qualcomm build host, keep ONNX blobs and artifacts outside Git and run:

```sh
python3 tools/release/mvl_model_artifacts.py record \
  --source "$SOURCE_ROOT" --onnx-assets "$ONNX_BLOBS" \
  --artifacts "$QCOM_OUTPUTS" --agnos-image "$AGNOS_IMAGE" \
  --agnos-root "$EXTRACTED_AGNOS_ROOT" --manifest "$PACKAGE_MANIFEST"
python3 tools/release/mvl_model_artifacts.py verify \
  --source "$SOURCE_ROOT" --onnx-assets "$ONNX_BLOBS" \
  --artifacts "$QCOM_OUTPUTS" --agnos-image "$AGNOS_IMAGE" \
  --agnos-root "$EXTRACTED_AGNOS_ROOT" --manifest "$PACKAGE_MANIFEST"
```

Preserve the original manifest. A manifest is a reproducible identity record, **not** an attestation of who built the binaries. Review build logs and capture a real comma 4 inference/boot result before any build or release gate promotion. This tool does not import the package into SCons and cannot make an incomplete build installable.

## Current inputs and HOLD decision

The preserved audit tree provides real ONNX blobs matching the pinned MVL LFS pointers: `dmonitoring_model.onnx` 7,844,499 bytes, SHA-256 `dee5a294e8afaacc9295ac5d100e00733ecac278e79264b96331e40a3ede1b04`; `driving_supercombo.onnx` 60,918,562 bytes, SHA-256 `65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce`. These are source inputs, not compiled QCOM outputs.

The audit tree's six generated tinygrad files contain CPU/LLVM backend tokens and fail static QCOM capture inspection. The local Dom package has five hash-matched QCOM captures, but lacks MVL's required `driving_tinygrad.pkl`. Its manifest binds a different source inventory: comparison with pinned MVL found 131 differing source hashes and 16 missing files among 578 listed sources. Dom retired its driving target and uses a different tinygrad compiler/runtime path. Its manifest SHA-256 was `ca1deae7c3be7c867a6ea5afaf96d80a4213418540802d7a902d485de1e4f204` at inspection. The Dom package is a design reference only; direct reuse is HOLD.

The isolated Ubuntu builder has no `/dev/kgsl-3d0` Qualcomm runtime. Obtain a complete, source-matched QCOM package from an approved comma 4 build route, then run this preflight and target runtime tests. Keep current known-good installation and AGNOS reference unchanged.
