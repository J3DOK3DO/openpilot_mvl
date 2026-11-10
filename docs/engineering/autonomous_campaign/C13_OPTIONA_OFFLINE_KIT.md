# Campaign 13 Option A offline display engineering kit

`tools/release/c13_optiona.py` inventories the frozen functional UI source and AGNOS 19.9. It never imports or starts production UI. With no `--output`, preflight writes nothing. An explicit output may only be a direct child of the C13 artifacts directory. `package` creates a non-installable directory containing only `status.py`, its manifest, and a warning README. Production UI files are hash inventory only; no vehicle-facing source is packaged.

The source under `MVL_AGNOS199_NATIVE_20261106/source_4b25263` is pinned to `4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb`; C13 is based on `01b2a79367c2b6f33fa764a0c7a8e9e4e63a2392`. The C12 branch itself contains documentation, not a newly built dashboard. The original `ui.py` enters messaging and real time UI state, so it is not a safe standalone preview.

The AGNOS rootfs contains a genuine AArch64 raylib extension. Static ELF inspection is retained as dependency evidence only. Host Python lacks `pyray` and `cffi`; a native host UI preview and target runtime execution remain unverified. The direct native status pytest skips for missing `pyray`. The package is not installable, launchable UI, or release evidence.

To review offline, inspect `C13_OPTIONA_PREFLIGHT.json`, `C13_OPTIONA_HANDOFF_MANIFEST.json`, the packaged `manifest.json`, `C13_RAYLIB_ELF.log`, tests and `SHA256SUMS`. Run `python3 tools/release/c13_optiona.py preflight` read only. Do not use production launch or release scripts for this kit. Option B has its own stage gates in the artifacts directory.
