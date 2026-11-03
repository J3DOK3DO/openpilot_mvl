#!/usr/bin/env python3
"""G10 read-only AGNOS compatibility inventory, never builds/flashes a device."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
from pathlib import Path

DEFAULT_AGNOS = Path("/home/jdkd/AGNOS_20261014/agnos_system.ext4.img")
NATIVE_MVL = Path("/mnt/commadrive/MVL_NATIVE_LATEST_20261103")
FROZEN_MVL = "376c44b5731b2655e5c2f301b73c9729eb499e91"
FROZEN_IMAGE_SHA256 = "98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8"

def run_readonly(args: list[str], max_bytes: int = 5000) -> str:
  # Exact command allowlist; never allow debugfs -w or -z, mounting or sudo.
  assert args[0] in ("git", "debugfs", "file")
  if args[0] == "debugfs":
    assert len(args) == 4 and args[1] == "-R" and args[2] in ("cat /VERSION", "cat /etc/issue")
  if args[0] == "git":
    assert len(args) == 5 and args[1] == "-C" and args[3:] == ["rev-parse", "HEAD"]
  if args[0] == "file":
    assert len(args) == 2
  try:
    result = subprocess.run(args, capture_output=True, text=True, timeout=20, check=False)
    return (result.stdout + result.stderr)[:max_bytes].strip()
  except (OSError, subprocess.TimeoutExpired) as exc:
    return f"UNAVAILABLE:{type(exc).__name__}"

def bounded_hash(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as src:
    while block := src.read(4 * 1024 * 1024):
      digest.update(block)
  return digest.hexdigest()

def elf_machine(path: Path) -> dict:
  if not path.is_file():
    return {"path": str(path), "status": "MISSING"}
  with path.open("rb") as f:
    hdr=f.read(24)
  if hdr[:4] != b"\x7fELF":
    return {"path":str(path),"status":"NOT_ELF"}
  if hdr[4] != 2 or hdr[5] not in (1,2):
    return {"path":str(path),"status":"UNSUPPORTED_HEADER"}
  machine=struct.unpack("<H" if hdr[5] == 1 else ">H", hdr[18:20])[0]
  return {"path":str(path),"status":"INSPECTED","elf_machine":machine,
          "architecture":{62:"x86_64",183:"aarch64"}.get(machine,"OTHER")}

def report(image: Path, checkout: Path, workspace: Path) -> dict:
  if not image.is_file():
    return {"status":"HOLD_MISSING_IMAGE","image":str(image)}
  version=run_readonly(["debugfs","-R","cat /VERSION",str(image)])
  issue=run_readonly(["debugfs","-R","cat /etc/issue",str(image)])
  sha=bounded_hash(image)
  head=run_readonly(["git","-C",str(checkout),"rev-parse","HEAD"])
  drive=shutil.disk_usage(workspace)
  targets=[
    checkout/"openpilot/common/libparams_c.so",
    checkout/"msgq_repo/msgq/ipc_pyx.so",
  ]
  native_elf=[elf_machine(p) for p in targets]
  compilers={x:shutil.which(x) for x in ("aarch64-linux-gnu-gcc","aarch64-linux-gnu-g++","clang","qemu-aarch64-static","readelf","debugfs")}
  failures=[]
  if sha != FROZEN_IMAGE_SHA256: failures.append("AGNOS_IMAGE_HASH_DRIFT")
  if not version.splitlines()[0].strip() == "19.8.1": failures.append("AGNOS_VERSION_MISMATCH")
  if head != FROZEN_MVL: failures.append("SOURCE_PIN_DRIFT")
  if drive.free < 15 * 1024**3: failures.append("INSUFFICIENT_DEDICATED_BUILD_DISK")
  if not compilers["aarch64-linux-gnu-gcc"]: failures.append("NO_TARGET_CROSS_GCC")
  if any(x["architecture"]!="aarch64" for x in native_elf if x["status"]=="INSPECTED"):failures.append("HOST_X86_BINARIES_NOT_TARGET")
  return {"classification":"PASSIVE_PREPARATION_ONLY","status":"HOLD_FOR_ARM64_BUILD_AND_DEVICE",
      "source_pin":head,"agnos_image":str(image),"agnos_sha256":sha,"agnos_version_raw":version,"agnos_issue_raw":issue,
      "host_machine":platform.machine(),"native_binary_elfs":native_elf,"toolchain":compilers,
      "build_drive_bytes_free":drive.free,"build_drive_bytes_total":drive.total,
      "open_gates":failures,
      "no_device_contact":True,"no_firmware_flash":True,"no_uds_can":True,
      "next_evidence":["full clean AArch64 build","dependency/RUNPATH closure on exact sysroot",
        "verified device AGNOS and Panda identities","isolated bench boot, resource and recovery",
        "OEM Honda collision-mitigation verification"]}

def main() -> None:
  parser=argparse.ArgumentParser()
  parser.add_argument("--image",type=Path,default=DEFAULT_AGNOS)
  parser.add_argument("--native-checkout",type=Path,default=NATIVE_MVL)
  parser.add_argument("--workspace",type=Path,default=Path("/mnt/commadrive"))
  parser.add_argument("--output",type=Path)
  args=parser.parse_args()
  result=report(args.image,args.native_checkout,args.workspace)
  payload=json.dumps(result,indent=2)+"\n"
  if args.output:
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(payload,encoding="utf-8")
  print(payload)

if __name__ == "__main__":
  main()
