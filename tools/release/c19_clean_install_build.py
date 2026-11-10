#!/usr/bin/env python3
"""Build and verify the deterministic minimal clean-install payload."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_FILES = (
  "LICENSE", "LICENSE.md", "launch_openpilot.sh", "launch_chffrplus.sh",
  "displayonly/c19_display.py", "displayonly/launch.sh",
)
FORBIDDEN = ("manager.py", "sendcan", "PubMaster", "Params(", "agnos.py", "abctl",
             "sudo", "/dev/panda", "openpilot.system.manager", "panda.python")


def digest_bytes(value: bytes) -> str:
  return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
  value = hashlib.sha256()
  with path.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
      value.update(chunk)
  return value.hexdigest()


def collect() -> tuple[dict[str, bytes], dict]:
  entries = {}
  for relative in PAYLOAD_FILES:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
      raise ValueError(f"unsafe or absent payload source: {relative}")
    entries[relative] = path.read_bytes()
  runtime_text = b"\n".join(entries[name] for name in entries if name.endswith((".py", ".sh"))).decode()
  found = sorted(token for token in FORBIDDEN if token in runtime_text)
  if found:
    raise ValueError(f"forbidden runtime mechanisms: {found}")
  manifest = {
    "schema": "c19-clean-install-payload-v1",
    "classification": "CLEAN_INSTALL_OFFLINE_CANDIDATE",
    "target": "Comma 4 MICI / AGNOS 19.9 / AArch64",
    "files": {name: {"sha256": digest_bytes(data), "bytes": len(data)}
              for name, data in sorted(entries.items())},
    "runtime_dependencies": ["/usr/local/venv/bin/python", "pyray", "raylib comma backend",
                             "/tmp/drmfd.sock", "/dev/dri/card0"],
    "runtime_imports_cereal": False,
    "runtime_uses_params": False,
    "runtime_publishers": [],
    "manager_or_vehicle_processes": [],
    "actuation_allowed": False,
    "physical_graphics_qualified": False,
  }
  entries["C19_RUNTIME_MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
  return entries, manifest


def build(output: Path) -> dict:
  entries, manifest = collect()
  with output.open("xb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
      with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
        directory = tarfile.TarInfo("openpilot")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        directory.mtime = directory.uid = directory.gid = 0
        directory.uname = directory.gname = "root"
        archive.addfile(directory)
        for name, data in sorted(entries.items()):
          info = tarfile.TarInfo(f"openpilot/{name}")
          info.size = len(data)
          info.mtime = info.uid = info.gid = 0
          info.uname = info.gname = "root"
          info.mode = 0o755 if name.endswith((".py", ".sh")) else 0o644
          archive.addfile(info, io.BytesIO(data))
  with tempfile.TemporaryDirectory(prefix="c19-clean-build-") as temporary:
    stage = Path(temporary).resolve()
    with tarfile.open(output, "r:gz") as archive:
      for member in archive.getmembers():
        target = (stage / member.name).resolve()
        if not target.is_relative_to(stage) or member.issym() or member.islnk():
          raise ValueError(f"unsafe archive member: {member.name}")
      archive.extractall(stage, filter="data")
    unpacked = stage / "openpilot"
    actual = {str(path.relative_to(unpacked)) for path in unpacked.rglob("*") if path.is_file()}
    expected = set(entries)
    if actual != expected:
      raise ValueError(f"payload membership mismatch: {sorted(actual ^ expected)}")
    for name, data in entries.items():
      if (unpacked / name).read_bytes() != data:
        raise ValueError(f"payload bytes mismatch: {name}")
    subprocess.run(["bash", "-n", str(unpacked / "launch_openpilot.sh")], check=True)
    subprocess.run(["bash", "-n", str(unpacked / "displayonly/launch.sh")], check=True)
    subprocess.run(["python3", "-m", "py_compile", str(unpacked / "displayonly/c19_display.py")],
                   check=True, env={"PYTHONPYCACHEPREFIX": str(stage / "pycache")})
  return {
    "schema": "c19-clean-install-build-v1", "result": "PASS",
    "archive_sha256": digest(output), "archive_bytes": output.stat().st_size,
    "deterministic_metadata": True, "safe_extraction": True,
    "payload_files": len(entries), "manifest": manifest,
  }


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output", type=Path, required=True)
  parser.add_argument("--result", type=Path)
  args = parser.parse_args()
  if not args.output.is_absolute() or not args.output.parent.is_dir() or args.output.exists():
    raise ValueError("output must be a new absolute file in an existing directory")
  result = build(args.output)
  text = json.dumps(result, indent=2, sort_keys=True) + "\n"
  if args.result:
    args.result.write_text(text, encoding="utf-8")
  print(text, end="")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
