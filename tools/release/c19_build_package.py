#!/usr/bin/env python3
"""Build the deterministic C19 dependency-closure-remediated native candidate."""
from __future__ import annotations

import argparse
import gzip
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

try:
  from tools.release import c18_build_package as c18
except ModuleNotFoundError:
  import c18_build_package as c18


WORKTREE = Path(__file__).resolve().parents[2]
ROOT_NAME = "C19_NATIVE_UI_OFFLINE_CANDIDATE"
ARCHIVE_NAME = ROOT_NAME + ".tar.gz"
C18_ARCHIVE_SHA256 = "449624da60c90fdc667740c08153622d6d0ec721f0adaef1e7508ba181b57634"


def build(output: Path, release_commit: str) -> tuple[dict, dict]:
  entries, audit = c18.collect_entries()
  required_remediation = "runtime/openpilot/sunnypilot/starpilot_bridge/adapter.py"
  if required_remediation not in entries:
    raise ValueError("relative-import closure remediation is absent")
  file_manifest = {name: {"sha256": c18.sha256_bytes(data), "bytes": len(data)}
                   for name, data in sorted(entries.items())}
  manifest = {
    "format": 1, "campaign": "C19", "classification": "NATIVE_UI_OFFLINE_CANDIDATE",
    "source_commit": c18.SOURCE_SHA, "release_engineering_commit": release_commit,
    "target": "Comma 4 / AGNOS 19.9 / AArch64", "files": file_manifest,
    "audit": audit, "install_allowed": False, "actuation_allowed": False,
    "remediates_candidate_sha256": C18_ARCHIVE_SHA256,
    "remediation": "complete recursive absolute and relative Python import closure",
  }
  entries["MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
  with output.open("xb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
      with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(entries.items()):
          info = tarfile.TarInfo(f"{ROOT_NAME}/{name}")
          info.size = len(data)
          info.mtime = info.uid = info.gid = 0
          info.uname = info.gname = "root"
          info.mode = 0o755 if name.startswith("app/") else 0o644
          archive.addfile(info, io.BytesIO(data))
  with tempfile.TemporaryDirectory(prefix="c19-package-") as temporary:
    root = Path(temporary).resolve()
    with tarfile.open(output, "r:gz") as archive:
      for member in archive.getmembers():
        destination = (root / member.name).resolve()
        if not destination.is_relative_to(root) or member.issym() or member.islnk():
          raise ValueError(f"unsafe archive member: {member.name}")
      archive.extractall(root, filter="data")
    unpacked = root / ROOT_NAME
    subprocess.run(["python3", str(unpacked / "app/c18_preflight.py"), "--package",
                    str(unpacked), "--rootfs",
                    "/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs"], check=True,
                   stdout=subprocess.DEVNULL)
  verification = {"archive_sha256": c18.sha256(output),
                  "archive_bytes": output.stat().st_size, "deterministic_metadata": True,
                  "safe_extraction": True, "offline_preflight": "PASS"}
  return manifest, verification


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output-dir", type=Path, required=True)
  args = parser.parse_args()
  if not args.output_dir.is_absolute() or not args.output_dir.is_dir() or args.output_dir.is_symlink():
    raise ValueError("output-dir must be an existing absolute real directory")
  release_commit = subprocess.check_output(
    ["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], text=True).strip()
  manifest, verification = build(args.output_dir / ARCHIVE_NAME, release_commit)
  for name, value in (("C19_NATIVE_UI_PACKAGE_MANIFEST.json", manifest),
                      ("C19_NATIVE_PACKAGE_BUILD_RESULTS.json", verification)):
    path = args.output_dir / name
    with path.open("x", encoding="utf-8") as stream:
      json.dump(value, stream, indent=2, sort_keys=True)
      stream.write("\n")
  print(json.dumps(verification, indent=2, sort_keys=True))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
