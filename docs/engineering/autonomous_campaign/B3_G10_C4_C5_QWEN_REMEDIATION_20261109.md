# Qwen3-Coder review remediation — B3/G10 combined readiness, 2026-11-09

## Disposition and review adjudication

The independent review identified a **valid snapshot trust defect** in two offline readers at baseline `d40f9d79d43004ac82d76872aab0f5e9b6323199`. Python `combined_device_gate.py` checked path metadata, then reopened the path with `read_bytes()`. A swapped symlink, FIFO or other special file could therefore defeat the precheck. Windows `b3_windows_readiness.ps1` used `Get-FileHash` and then `Get-Content`, leaving the displayed fields unbound to the verified bytes. The prior successful exit status for a blocked report could also mislead consumers. These are corrected in local code commit `00326a0f0329f6eb8905db51ee20df2e5c608d40`.

Two other reviewer assertions are **unsupported**. The Python `/dev/kgsl-3d0` check is a regular expression over saved text; it does not open a GPU node or run GPU work. The bounded AArch64 `libvisionipc.a` Docker build ran on the host and produced relocatable objects; it did not execute on Comma 4 or prove target runtime behavior. These assertions are not treated as verified defects or as device qualification.

## Corrected reader and CLI contract

Python now uses `lstat` before open to reject a nonregular leaf, symlink or file over 1 MiB, then opens with `O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC` where available. It checks `fstat` on that descriptor for regular type, matching device/inode and size, and reads at most 1 MiB + 1 byte. The SHA-256 and UTF-8-with-optional-BOM parser consume the same byte buffer. Unreadable, swapped, oversized, hash-mismatched or invalid UTF-8 input exits nonzero. A valid, pinned passive transcript produces JSON on stdout with `device_compile_allowed=false` and `install_allowed=false`, then exits **2** for `DEVICE_COMPILE_BLOCKED_UNVERIFIED_PARKED_OR_POWER_OR_RESOURCE`. There is no force option.

The Windows offline kit uses a single bounded Windows file handle. It rejects path reparse attributes, opens the leaf with `FILE_FLAG_OPEN_REPARSE_POINT`, checks the opened handle type/attributes/size and final path, then hashes and strictly decodes the bytes read from that handle. Duplicate selected fields are rejected; malformed flag values become `UNKNOWN`. Missing snapshot, validation errors and the blocked offline result exit **2**. Explicit `-RunReadOnly` remains authenticated SSH with `StrictHostKeyChecking=yes`, only passive shell reads, and exit **2** even when SSH succeeds. No Windows runtime execution was possible on this Ubuntu host; the coordinator will run PowerShell parser and behavior tests on Windows.

## Verified host results

At clean committed implementation HEAD `00326a0f0329f6eb8905db51ee20df2e5c608d40`:

| Check | Result | Retained local log SHA-256 |
| --- | --- | --- |
| Focused `test_combined_device_gate` | 9 passed, 0 skipped, 0 failed | `8abe6ea45b8678cf08ff74e15fd22bd04109abca59a04ba113267db6e3d3c11f` |
| Full `tools/release/tests` | 196 run, 187 passed, 9 platform skips, 0 failed | `31e509d5ddf5c469c20e5188ac942bd2ea51a6a47e7e8afb2889e4445f779c4c` |
| Native inspector and ABI | 10 passed, 0 skipped, 0 failed | `baadaac060a617ef9abc4e487344ff9c33db7d8e86d5b5c6df93b8888a0a02fe` |
| Campaign recovery | 4 passed, 0 skipped, 0 failed | `96719d6dc693d47aa327370177e852eb9736e48ad71810006c249529340ed1d3` |

Focused negatives cover symlink preopen, FIFO-mode special-file preopen without touching a FIFO, inode replacement between `lstat` and open, growth beyond the read limit, a pathname swap after descriptor read, wrong hash and invalid UTF-8. The same-buffer test uses BOM and CRLF. The actual pinned `COMMA4_PASSIVE_PREFLIGHT_20261109.txt` SHA-256 is `21f732825d9d61580e44e7c33e67cd9f8f4904884e84e96f284641529f13740d`; the guarded CLI exited **2** and emitted JSON SHA-256 `da795faaef367214ae8b26cd05107445a88c68ce2a2a8c720f3781bdf58b91d1`. Its AGNOS 19.9/AArch64 gate is PASS, installed source identity FAIL, sustained external power FAIL, and parked, GPU ABI, quota/peaks, thermal monitor, staged source and rollback remain UNKNOWN. The guarded logs and JSON are under `/tmp/b3_rem_*` in this session; hashes and counts above are the durable record.

## Residual HOLD

The transcript is only a passive point-in-time capture. The currently installed source differs from frozen G10; the offroad/ignition line is malformed and all observed external power supplies are offline. Target GPU/driver ABI, hard quota, peak resources, continuous safety monitors and device-tested recovery remain unproven. Genuine QCOM outputs are **0/6**, full G10 is **NOT_BUILT**, Comma 4 physical checks are **0/10**, and release is **RC_NOT_INSTALLABLE / HOLD**. Neither parsing success nor read-only SSH observation admits native compilation, installation or physical acceptance. No device contact, transfer, compilation, installation, vehicle/Panda/CAN action, lease change or push occurred in this remediation.
