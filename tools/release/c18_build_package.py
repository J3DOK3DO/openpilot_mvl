#!/usr/bin/env python3
"""Build the deterministic C18 native display-only offline candidate."""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

SOURCE_SHA = "4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb"
WORKTREE = Path(__file__).resolve().parents[2]
SOURCE = Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263")
ARM_SOURCE = Path("/mnt/commadrive/MVL_C14A_NATIVE_IPC_WORK_20261110")
NATIVE = ("msgq_repo/msgq/ipc_pyx.so", "msgq_repo/msgq/visionipc/visionipc_pyx.so",
          "openpilot/common/libparams_c.so")
SEED_PREFIXES = ("openpilot/cereal", "openpilot/common", "openpilot/selfdrive/assets",
                 "openpilot/selfdrive/ui", "openpilot/system/ui", "msgq_repo/msgq")
APP_FILES = ("c18_native_ui.py", "c18_preflight.py", "c18_native_ui.sh", "c18_supervise.sh")
FORBIDDEN_PARTS = {"manager", "controlsd", "pandad", "boardd", "modeld", "plannerd"}


def sha256_bytes(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
  return sha256_bytes(path.read_bytes())


def tracked(prefixes: tuple[str, ...]) -> set[str]:
  output = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "--", *prefixes], text=True)
  return {line for line in output.splitlines() if line}


def tracked_opendbc() -> set[str]:
  output = subprocess.check_output(["git", "-C", str(SOURCE / "opendbc_repo"),
                                    "ls-files", "--", "opendbc/car"], text=True)
  return {f"opendbc_repo/{line}" for line in output.splitlines() if line}


def resolve_module(module: str) -> str | None:
  roots = {"openpilot": "openpilot", "msgq": "msgq_repo/msgq", "opendbc": "opendbc_repo/opendbc"}
  top = module.split(".")[0]
  if top not in roots:
    return None
  suffix = module.split(".")[1:]
  base = Path(roots[top]).joinpath(*suffix)
  for candidate in (str(base) + ".py", str(base / "__init__.py")):
    if (SOURCE / candidate).is_file():
      return candidate
  return None


def source_closure() -> set[str]:
  files = tracked(SEED_PREFIXES)
  # cereal loads these schemas dynamically through importlib.resources; AST
  # import closure alone cannot discover them.
  files.update(name for name in tracked_opendbc()
               if name.endswith(".capnp"))
  files.add("opendbc_repo/opendbc/__init__.py")
  queue = [name for name in files if name.endswith(".py")]
  seen = set(queue)
  while queue:
    name = queue.pop()
    try:
      tree = ast.parse((SOURCE / name).read_text(), filename=name)
    except (SyntaxError, UnicodeDecodeError):
      continue
    modules = []
    for node in ast.walk(tree):
      if isinstance(node, ast.Import):
        modules.extend(alias.name for alias in node.names)
      elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        modules.append(node.module)
        modules.extend(f"{node.module}.{alias.name}" for alias in node.names
                       if alias.name != "*")
    for module in modules:
      target = resolve_module(module)
      if target and target not in files:
        files.add(target)
        if target not in seen:
          queue.append(target)
          seen.add(target)
        parent = Path(target).parent
        while str(parent) not in (".", ""):
          init = str(parent / "__init__.py")
          if (SOURCE / init).is_file():
            files.add(init)
          parent = parent.parent
  # Include declarative/runtime resources colocated with imported modules.
  # These are commonly opened by path rather than imported (for example the
  # offroad-alert definition), so they are not visible in an AST import graph.
  resource_suffixes = {".json", ".yaml", ".yml", ".capnp", ".txt", ".html", ".css",
                       ".ttf", ".otf", ".png", ".svg", ".wav", ".gif"}
  parents = {str(Path(name).parent) for name in files}
  files.update(name for name in tracked((".",))
               if str(Path(name).parent) in parents and Path(name).suffix.lower() in resource_suffixes)
  files.update({"openpilot/__init__.py", "msgq_repo/msgq/__init__.py"})
  # Repository-shipped device credentials are neither needed nor permitted in
  # this standalone display package.
  files = {name for name in files
           if Path(name).name.lower() not in {"id_rsa", "id_dsa"}
           and Path(name).suffix.lower() not in {".pem", ".key", ".p12", ".pfx"}}
  return files


def audit_entrypoint() -> None:
  text = (WORKTREE / "tools/release/c18_native_ui.py").read_text()
  tree = ast.parse(text)
  forbidden_calls = []
  for node in ast.walk(tree):
    if isinstance(node, ast.Call) and getattr(node.func, "attr", None) in ("PubMaster", "send"):
      forbidden_calls.append(getattr(node.func, "attr"))
  if forbidden_calls:
    raise ValueError(f"display entrypoint publishes messages: {forbidden_calls}")
  if any(token in text for token in ("LD_PRELOAD", "carControl", "Panda")):
    raise ValueError("forbidden production mechanism in entrypoint")


def collect_entries() -> tuple[dict[str, bytes], dict]:
  if subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip() != SOURCE_SHA:
    raise ValueError("frozen source identity mismatch")
  audit_entrypoint()
  entries: dict[str, bytes] = {}
  for name in APP_FILES:
    entries[f"app/{name}"] = (WORKTREE / "tools/release" / name).read_bytes()
  closure = source_closure()
  for rel in sorted(closure):
    path = SOURCE / rel
    if path.is_symlink():
      resolved = path.resolve()
      if not resolved.is_relative_to(SOURCE.resolve()) or not resolved.is_file():
        raise ValueError(f"unsafe source symlink: {rel}")
      path = resolved
    if not path.is_file():
      raise ValueError(f"unsafe source member: {rel}")
    entries[f"runtime/{rel}"] = path.read_bytes()
  native_inventory = []
  for rel in NATIVE:
    path = ARM_SOURCE / rel
    header = subprocess.check_output(["readelf", "-h", str(path)], text=True)
    dynamic = subprocess.check_output(["readelf", "-d", str(path)], text=True)
    if "ELF64" not in header or "AArch64" not in header:
      raise ValueError(f"wrong native ABI: {rel}")
    needed = sorted(line.split("[")[1].split("]")[0]
                    for line in dynamic.splitlines() if "(NEEDED)" in line)
    entries[f"runtime/{rel}"] = path.read_bytes()
    native_inventory.append({"path": f"runtime/{rel}", "sha256": sha256(path),
                             "bytes": path.stat().st_size, "needed": needed, "abi": "aarch64"})
  readme = """C18 NATIVE_UI_OFFLINE_CANDIDATE

This is a hash-sealed, non-actuating AGNOS 19.9 AArch64 display application.
It is not installation-approved. The launcher refuses execution without exact-candidate
P1-P7 authorization and aborts if control-related processes are present. It never starts
manager, controller, Panda, model, planning, radar, or CAN processes and publishes no IPC.
The AGNOS Python 3.12 platform runtime and genuine DRM/EGL/GLES/GBM stack are required.
"""
  entries["README.md"] = readme.encode()
  audit = {"source_commit": SOURCE_SHA, "runtime_source_files": len(closure),
           "native_binaries": native_inventory, "publisher_services": [],
           "manager_or_control_launcher_included": False, "ld_preload_used": False,
           "platform_runtime": "AGNOS 19.9 /usr/local/venv Python 3.12",
           "graphics_backend": "genuine raylib comma DRM/EGL/GLES/GBM",
           "physical_graphics_qualified": False}
  return entries, audit


def build(output: Path, release_commit: str) -> tuple[dict, dict]:
  entries, audit = collect_entries()
  file_manifest = {name: {"sha256": sha256_bytes(data), "bytes": len(data)}
                   for name, data in sorted(entries.items())}
  manifest = {"format": 1, "campaign": "C18", "classification": "NATIVE_UI_OFFLINE_CANDIDATE",
              "source_commit": SOURCE_SHA, "release_engineering_commit": release_commit,
              "target": "Comma 4 / AGNOS 19.9 / AArch64",
              "files": file_manifest, "audit": audit, "install_allowed": False,
              "actuation_allowed": False}
  entries["MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
  with output.open("xb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
      with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(entries.items()):
          info = tarfile.TarInfo(f"C18_NATIVE_UI_OFFLINE_CANDIDATE/{name}")
          info.size = len(data); info.mtime = 0; info.uid = info.gid = 0
          info.uname = info.gname = "root"
          info.mode = 0o755 if name.startswith("app/") else 0o644
          archive.addfile(info, io.BytesIO(data))
  with tempfile.TemporaryDirectory(prefix="c18-package-") as temporary:
    root = Path(temporary).resolve()
    with tarfile.open(output, "r:gz") as archive:
      for member in archive.getmembers():
        destination = (root / member.name).resolve()
        if not destination.is_relative_to(root) or member.issym() or member.islnk():
          raise ValueError(f"unsafe archive member: {member.name}")
      archive.extractall(root, filter="data")
    unpacked = root / "C18_NATIVE_UI_OFFLINE_CANDIDATE"
    subprocess.run(["python3", str(unpacked / "app/c18_preflight.py"), "--package", str(unpacked),
                    "--rootfs", "/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs"], check=True,
                   stdout=subprocess.DEVNULL)
  verification = {"archive_sha256": sha256(output), "archive_bytes": output.stat().st_size,
                  "deterministic_metadata": True, "safe_extraction": True,
                  "offline_preflight": "PASS"}
  return manifest, verification


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output-dir", type=Path, required=True)
  args = parser.parse_args()
  if not args.output_dir.is_absolute() or not args.output_dir.is_dir() or args.output_dir.is_symlink():
    raise ValueError("output-dir must be an existing absolute real directory")
  archive = args.output_dir / "C18_NATIVE_UI_OFFLINE_CANDIDATE.tar.gz"
  release_commit = subprocess.check_output(
    ["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], text=True).strip()
  if len(release_commit) != 40:
    raise ValueError("invalid release engineering commit identity")
  manifest, verification = build(archive, release_commit)
  for name, value in (("C18_NATIVE_UI_PACKAGE_MANIFEST.json", manifest),
                      ("C18_NATIVE_PACKAGE_BUILD_RESULTS.json", verification)):
    with (args.output_dir / name).open("x", encoding="utf-8") as stream:
      json.dump(value, stream, indent=2, sort_keys=True); stream.write("\n")
  print(json.dumps({"archive": str(archive), **verification}, indent=2, sort_keys=True))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
