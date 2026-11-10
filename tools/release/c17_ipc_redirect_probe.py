#!/usr/bin/env python3
"""Execute the C17 preload traversal regression in disposable storage only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "c17_ipc_redirect.c"


def run_call(library: Path, root: Path, expression: str) -> dict:
  env = os.environ.copy()
  env.update({"LD_PRELOAD": str(library), "C17_MSGQ_ROOT": str(root),
              "OPENPILOT_PREFIX": "c17_probe"})
  code = f'''
import ctypes, json, os
libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
ret = {expression}
print(json.dumps({{"return": ret, "errno": ctypes.get_errno()}}))
'''
  proc = subprocess.run(["python3", "-c", code], env=env, text=True,
                        capture_output=True, check=True)
  return json.loads(proc.stdout)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()
  if not args.output.is_absolute() or args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
    raise ValueError("output must be a new absolute direct file in an existing directory")

  with tempfile.TemporaryDirectory(prefix="c17-ipc-probe-") as tmp:
    base = Path(tmp).resolve()
    root = base / "private"
    (root / "msgq_c17_probe").mkdir(parents=True)
    (root / "event").mkdir()
    library = base / "redirect.so"
    subprocess.run(["cc", "-shared", "-fPIC", "-O2", "-Wall", "-Wextra", "-Werror",
                    str(SOURCE), "-ldl", "-o", str(library)], check=True)
    calls = {
      "open": 'libc.open(b"/dev/shm/msgq_c17_probe/../../../victim", os.O_WRONLY | os.O_TRUNC, 0)',
      "open64": 'libc.open64(b"/dev/shm/msgq_c17_probe/../../../victim", os.O_WRONLY | os.O_TRUNC, 0)',
      "shm_unlink": 'libc.shm_unlink(b"/msgq_/../../../victim")',
    }
    cases = []
    for operation, expression in calls.items():
      victim = base / "victim"
      victim.write_text("C17_CANARY_MUST_SURVIVE")
      result = run_call(library, root, expression)
      survived = victim.is_file() and victim.read_text() == "C17_CANARY_MUST_SURVIVE"
      cases.append({"operation": operation, **result, "expected_errno": 22,
                    "canary_survived": survived, "pass": survived and result == {"return": -1, "errno": 22}})

    valid = run_call(library, root,
                     'libc.open(b"/dev/shm/msgq_c17_probe/deviceState", os.O_CREAT | os.O_RDWR, 0o600)')
    report = {
      "campaign": "C17_HARDENING",
      "scope": "disposable host temp directory; no host /dev/shm or device",
      "shim_source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      "malicious_cases": cases,
      "all_canaries_survived": all(case["canary_survived"] for case in cases),
      "all_malicious_calls_rejected_einval": all(case["pass"] for case in cases),
      "legitimate_open_succeeded": valid["return"] >= 0 and (root / "msgq_c17_probe" / "deviceState").is_file(),
    }
  with args.output.open("x") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
  print(json.dumps(report, sort_keys=True))
  return 0 if all((report["all_canaries_survived"], report["all_malicious_calls_rejected_einval"],
                   report["legitimate_open_succeeded"])) else 1


if __name__ == "__main__":
  raise SystemExit(main())
