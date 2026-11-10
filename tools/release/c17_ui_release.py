#!/usr/bin/env python3
"""Audit and package the C17 non-installable host-only display bench."""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import tempfile

SOURCE_SHA = "4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb"
WORKTREE = Path(__file__).resolve().parents[2]
HOST_SOURCE = Path("/mnt/commadrive/MVL_C15_HOST_UI_SOURCE_20261110")
ARM_SOURCE = Path("/mnt/commadrive/MVL_C14A_NATIVE_IPC_WORK_20261110")
FROZEN_SOURCE = Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263")
ROOTFS = Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs")
NATIVE = ("msgq_repo/msgq/ipc_pyx.so", "msgq_repo/msgq/visionipc/visionipc_pyx.so",
          "openpilot/common/libparams_c.so")
PACKAGE_FILES = ("c17_standalone_ui.sh", "c17_standalone_ui.py",
                 "c17_device_state_publisher.py", "c17_ipc_redirect.c",
                 "c17_ipc_redirect_probe.py")


def sha256(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def git_head(path: Path) -> str:
  return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def git_index_and_untracked_clean(path: Path) -> bool:
  cached = subprocess.run(["git", "-C", str(path), "diff-index", "--cached", "--quiet", "HEAD", "--"])
  untracked = subprocess.check_output(
    ["git", "-C", str(path), "ls-files", "--others", "--exclude-standard"], text=True).strip()
  return cached.returncode == 0 and untracked == ""


def tree_digest(path: Path, prefixes: tuple[str, ...]) -> tuple[str, int]:
  names = subprocess.check_output(["git", "-C", str(path), "ls-files", "--", *prefixes], text=True).splitlines()
  digest = hashlib.sha256()
  count = 0
  for name in names:
    candidate = path / name
    if not candidate.is_file() or candidate.is_symlink():
      raise ValueError(f"missing or symlinked tracked runtime source: {candidate}")
    digest.update(name.encode() + b"\0")
    digest.update(hashlib.sha256(candidate.read_bytes()).digest())
    count += 1
  return digest.hexdigest(), count


def safe_new_output(root: Path, name: str) -> Path:
  if (not root.is_absolute() or not root.is_dir() or root.is_symlink()
      or root.resolve() != root or "/" in name or name in ("", ".", "..")):
    raise ValueError("unsafe output directory or name")
  target = root / name
  if target.exists() or target.is_symlink():
    raise FileExistsError(f"refusing overwrite: {target}")
  return target


def audit_pubmaster() -> dict:
  calls = []
  for name in ("c17_standalone_ui.py", "c17_device_state_publisher.py"):
    path = WORKTREE / "tools/release" / name
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
      if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "PubMaster":
        services = ast.literal_eval(node.args[0])
        if services != ["deviceState"]:
          raise ValueError(f"forbidden PubMaster services in {name}: {services}")
        calls.append({"path": name, "services": services})
      if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "send":
        if not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value != "deviceState":
          raise ValueError(f"forbidden or dynamic publish call in {name}")
  if calls != [{"path": "c17_device_state_publisher.py", "services": ["deviceState"]}]:
    raise ValueError("expected exactly one deviceState-only PubMaster")
  return {"pubmaster_calls": calls, "device_control_publication_structurally_present": False}


def audit_runtime() -> dict:
  identities = {}
  for label, source in (("host", HOST_SOURCE), ("arm64", ARM_SOURCE), ("frozen", FROZEN_SOURCE)):
    head = git_head(source)
    if head != SOURCE_SHA or not git_index_and_untracked_clean(source):
      raise ValueError(f"source identity/index/untracked failure: {source}")
    identities[label] = {"path": str(source), "commit": head,
                         "index_matches_head": True, "untracked_files": 0}
  critical_prefixes = ("openpilot/selfdrive/ui", "openpilot/system/ui", "openpilot/common/params.py",
                       "openpilot/common/params.cc", "openpilot/common/params_c.cc")
  critical = {label: tree_digest(source, critical_prefixes)
              for label, source in (("host", HOST_SOURCE), ("arm64", ARM_SOURCE), ("frozen", FROZEN_SOURCE))}
  if len({value[0] for value in critical.values()}) != 1:
    raise ValueError(f"critical UI/Params source differs across pinned trees: {critical}")
  for label in identities:
    identities[label]["critical_runtime_tree_sha256"] = critical[label][0]
    identities[label]["critical_runtime_file_count"] = critical[label][1]
  if (ROOTFS / "VERSION").read_text().strip() != "19.9":
    raise ValueError("AGNOS rootfs version mismatch")

  font_prefix = "openpilot/selfdrive/assets/fonts/"
  tracked = subprocess.check_output(
    ["git", "-C", str(FROZEN_SOURCE), "ls-files", "--", font_prefix], text=True).splitlines()
  if len(tracked) != 17:
    raise ValueError(f"expected 17 tracked fonts, found {len(tracked)}")
  fonts = []
  for rel in tracked:
    origin = FROZEN_SOURCE / rel
    expected = sha256(origin)
    if origin.is_symlink() or not origin.is_file() or origin.stat().st_size < 1024:
      raise ValueError(f"invalid font: {rel}")
    for source in (HOST_SOURCE, ARM_SOURCE):
      candidate = source / rel
      if candidate.is_symlink() or sha256(candidate) != expected:
        raise ValueError(f"untrusted/mismatched font: {candidate}")
    fonts.append({"path": rel, "sha256": expected, "bytes": origin.stat().st_size})

  binaries = []
  for rel in NATIVE:
    for abi, source, machine in (
      ("x86_64", HOST_SOURCE, "Advanced Micro Devices X86-64"),
      ("aarch64", ARM_SOURCE, "AArch64"),
    ):
      path = source / rel
      header = subprocess.check_output(["readelf", "-h", str(path)], text=True)
      if "ELF64" not in header or machine not in header:
        raise ValueError(f"wrong ABI: {path}")
      deps = subprocess.run(["readelf", "-d", str(path)], text=True, capture_output=True, check=True).stdout
      needed = sorted(line.split("[")[1].split("]")[0] for line in deps.splitlines() if "(NEEDED)" in line)
      binaries.append({"path": rel, "abi": abi, "sha256": sha256(path),
                       "bytes": path.stat().st_size, "needed": needed})

  ui_entry = HOST_SOURCE / "openpilot/selfdrive/ui/ui.py"
  entry_text = ui_entry.read_text()
  expected_markers = ("config_realtime_process", "gui_app.init_window", "MainLayout()",
                      "MiciMainLayout()", "PubMaster(['uiDebug'])", "ui_state.update()")
  if any(marker not in entry_text for marker in expected_markers):
    raise ValueError("authentic UI entrypoint audit markers changed")
  return {
    "source_identities": identities,
    "agnos_version": "19.9",
    "authentic_ui_entrypoint": {"path": "openpilot/selfdrive/ui/ui.py", "sha256": sha256(ui_entry),
      "bench_reuses": ["GuiApplication", "MainLayout", "MiciMainLayout", "ui_state.SubMaster"],
      "intentionally_omitted_side_effects": ["real-time scheduling", "CPU affinity", "uiDebug publication"]},
    "fonts": fonts,
    "native_binaries": binaries,
    **audit_pubmaster(),
  }


def package_readme() -> str:
  return """C17 NON_INSTALLABLE_HOST_BENCH

This archive is not a Comma package, installer, product runtime, or hardware qualification.
Run ./c17_standalone_ui.sh with --layout and --output on the pinned C15 x86_64 host runtime.
It imports authentic frozen MVL UI classes but externally requires the exact source checkout,
x86_64 Python environment, Xvfb, Mesa, a C compiler, and system libraries listed in MANIFEST.json.
It contains no QCOM artifacts, model replacement, deploy script, vehicle Params, route logs,
credentials, Panda/CAN code, firmware, or device installer. Do not install it on a Comma device.
"""


def build_package(output: Path, audit: dict) -> tuple[dict, dict]:
  entries: dict[str, bytes] = {}
  for name in PACKAGE_FILES:
    entries[name] = (WORKTREE / "tools/release" / name).read_bytes()
  entries["README_DO_NOT_INSTALL.txt"] = package_readme().encode()
  dependency = {
    "classification": "NON_INSTALLABLE_HOST_BENCH",
    "external_runtime_required": True,
    "host_source": str(HOST_SOURCE),
    "host_source_commit": SOURCE_SHA,
    "python": "/mnt/commadrive/.venv-native15/bin/python",
    "required_commands": ["bash", "cc", "git", "Xvfb", "xdpyinfo"],
    "required_environment": ["x86_64 Linux", "X11", "Mesa software OpenGL"],
    "pyproject_sha256": sha256(HOST_SOURCE / "pyproject.toml"),
    "uv_lock_sha256": sha256(HOST_SOURCE / "uv.lock"),
    "missing_for_comma_product": ["physical Adreno/display proof", "authenticated QCOM model artifacts",
      "full product runtime", "device backup/restore evidence", "device-specific install approval"],
  }
  entries["DEPENDENCIES.json"] = (json.dumps(dependency, indent=2, sort_keys=True) + "\n").encode()
  file_manifest = {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                   for name, data in sorted(entries.items())}
  manifest = {"format": 1, "classification": "NON_INSTALLABLE_HOST_BENCH",
              "source_commit": SOURCE_SHA, "files": file_manifest,
              "verified_external_fonts": audit["fonts"],
              "verified_external_native_binaries": audit["native_binaries"],
              "device_install_allowed": False, "actuation_allowed": False}
  entries["MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()

  with output.open("xb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
      with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(entries.items()):
          info = tarfile.TarInfo(f"C17_NON_INSTALLABLE_HOST_BENCH/{name}")
          info.size = len(data)
          info.mtime = 0
          info.uid = info.gid = 0
          info.uname = info.gname = "root"
          info.mode = 0o755 if name.endswith((".sh", ".py")) else 0o644
          archive.addfile(info, io.BytesIO(data))

  with tempfile.TemporaryDirectory(prefix="c17-package-check-") as tmp:
    root = Path(tmp).resolve()
    with tarfile.open(output, "r:gz") as archive:
      for member in archive.getmembers():
        destination = (root / member.name).resolve()
        if not destination.is_relative_to(root) or member.issym() or member.islnk():
          raise ValueError(f"unsafe archive member: {member.name}")
      archive.extractall(root, filter="data")
    unpacked = root / "C17_NON_INSTALLABLE_HOST_BENCH"
    for name, expected in file_manifest.items():
      if sha256(unpacked / name) != expected["sha256"]:
        raise ValueError(f"unpacked package hash mismatch: {name}")
    unpacked_manifest = json.loads((unpacked / "MANIFEST.json").read_text())
    if unpacked_manifest != manifest:
      raise ValueError("unpacked manifest mismatch")
  verification = {"archive_sha256": sha256(output), "archive_bytes": output.stat().st_size,
                  "unpack_traversal_check": "PASS", "unpacked_hash_check": "PASS",
                  "symlink_members": 0, "classification": "NON_INSTALLABLE_HOST_BENCH"}
  return manifest, verification


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output-dir", type=Path, required=True)
  parser.add_argument("--archive-name", default="C17_NON_INSTALLABLE_HOST_BENCH.tar.gz")
  parser.add_argument("--readiness-name", default="C17_STANDALONE_UI_BENCH_READINESS.json")
  parser.add_argument("--manifest-name")
  args = parser.parse_args()
  audit = audit_runtime()
  archive = safe_new_output(args.output_dir, args.archive_name)
  manifest, verification = build_package(archive, audit)
  if args.manifest_name is not None:
    manifest_path = safe_new_output(args.output_dir, args.manifest_name)
    with manifest_path.open("x") as stream:
      json.dump({"package_manifest": manifest, "verification": verification}, stream,
                indent=2, sort_keys=True)
      stream.write("\n")
  readiness = {
    "campaign": "C17", "status": "OFFLINE_HOST_BENCH_READY_PHYSICAL_HOLD",
    "source_commit": SOURCE_SHA, "source_modified": False,
    "single_entrypoint": "c17_standalone_ui.sh", "authentic_ui_classes": True,
    "host_ipc": "genuine native msgq redirected to private /tmp backing",
    "publisher_services": ["deviceState"], "device_state_started": False,
    "ipc_health_labels": {"continuous": "HOST_FIXTURE_CONTINUOUS_FRESH only when fresh at exit",
      "terminate": "DEGRADED_PUBLISHER_TERMINATED_*", "absent": "DEGRADED_NO_PUBLISHER"},
    "vehicle_control_publication": False, "manager_started": False,
    "package": verification, "package_manifest": manifest, "audit": audit,
    "agnos_physical_gpu_qualified": False, "physical_comma_tested": False,
    "backup_verified": False, "restore_rehearsed": False, "device_install_allowed": False,
    "review_status": "INDEPENDENT_REVIEW_PENDING",
  }
  readiness_path = safe_new_output(args.output_dir, args.readiness_name)
  with readiness_path.open("x") as stream:
    json.dump(readiness, stream, indent=2, sort_keys=True)
    stream.write("\n")
  print(json.dumps({"readiness": str(readiness_path), "archive": str(archive), **verification}, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
