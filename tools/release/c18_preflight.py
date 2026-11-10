#!/usr/bin/env python3
"""Validate the sealed C18 package and AGNOS 19.9 compatibility without installation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

NATIVE = ("runtime/msgq_repo/msgq/ipc_pyx.so",
          "runtime/msgq_repo/msgq/visionipc/visionipc_pyx.so",
          "runtime/openpilot/common/libparams_c.so")
SYSTEM_LIBS = ("libc.so.6", "libstdc++.so.6", "libgcc_s.so.1", "libm.so.6",
               "libEGL.so.1", "libGLESv2.so.2", "libgbm.so.1", "libdrm.so.2")


def sha256(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
      h.update(chunk)
  return h.hexdigest()


def elf(path: Path, machine: str = "AArch64") -> dict:
  header = subprocess.check_output(["readelf", "-h", str(path)], text=True)
  dynamic = subprocess.check_output(["readelf", "-d", str(path)], text=True)
  if "ELF64" not in header or machine not in header:
    raise ValueError(f"wrong ELF ABI: {path}")
  needed = sorted(line.split("[")[1].split("]")[0]
                  for line in dynamic.splitlines() if "(NEEDED)" in line)
  return {"path": str(path), "sha256": sha256(path), "needed": needed}


def validate_package(root: Path) -> dict:
  root = root.resolve()
  if not root.is_dir() or root.is_symlink():
    raise ValueError("package root must be a real directory")
  manifest = json.loads((root / "MANIFEST.json").read_text())
  if manifest["classification"] != "NATIVE_UI_OFFLINE_CANDIDATE":
    raise ValueError("unsafe package classification")
  for rel, expected in manifest["files"].items():
    path = root / rel
    if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
      raise ValueError(f"unsafe or missing package file: {rel}")
    if sha256(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
      raise ValueError(f"package file mismatch: {rel}")
  actual = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
  expected = set(manifest["files"]) | {"MANIFEST.json"}
  if actual != expected:
    raise ValueError(f"unexpected package content: {sorted(actual ^ expected)[:10]}")
  binaries = [elf(root / rel) for rel in NATIVE]
  return {"manifest_sha256": sha256(root / "MANIFEST.json"), "files": len(actual),
          "native_binaries": binaries, "package_integrity": "PASS"}


def validate_rootfs(rootfs: Path) -> dict:
  rootfs = rootfs.resolve()
  if (rootfs / "VERSION").read_text().strip() != "19.9":
    raise ValueError("AGNOS version is not 19.9")
  python = rootfs / "usr/bin/python3.12"
  py = elf(python)
  library_roots = (rootfs / "usr/lib/aarch64-linux-gnu", rootfs / "lib/aarch64-linux-gnu")
  resolved = {}
  for name in SYSTEM_LIBS:
    matches = [base / name for base in library_roots if (base / name).exists()]
    if not matches:
      raise ValueError(f"AGNOS library missing: {name}")
    resolved[name] = str(matches[0].relative_to(rootfs))
  raylib = rootfs / "usr/local/venv/lib/python3.12/site-packages/raylib/_raylib_cffi_comma.abi3.so"
  ray = elf(raylib)
  required_graphics = {"libEGL.so.1", "libGLESv2.so.2", "libgbm.so.1", "libdrm.so.2"}
  if not required_graphics.issubset(ray["needed"]):
    raise ValueError("Raylib comma backend lacks authentic DRM/EGL dependency set")
  return {"agnos_version": "19.9", "python": py, "system_libraries": resolved,
          "raylib_comma_backend": ray, "graphics_hardware_executed": False,
          "rootfs_compatibility": "PASS"}


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--package", type=Path, required=True)
  parser.add_argument("--rootfs", type=Path, required=True)
  parser.add_argument("--output", type=Path)
  args = parser.parse_args()
  result = {"campaign": "C18", "package": validate_package(args.package),
            "agnos": validate_rootfs(args.rootfs), "result": "PASS",
            "physical_device_tested": False}
  text = json.dumps(result, indent=2, sort_keys=True) + "\n"
  if args.output:
    with args.output.open("x", encoding="utf-8") as stream:
      stream.write(text)
  print(text, end="")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
