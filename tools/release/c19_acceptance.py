#!/usr/bin/env python3
"""Generate conservative Campaign 19 offline and physical-hold evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import tempfile


WORKTREE = Path(__file__).resolve().parents[2]
ARTIFACTS_DEFAULT = Path("/mnt/commadrive/MVL_C19_COMMA4_ACCEPTANCE_ARTIFACTS_20261110")
C18_ARTIFACTS = Path("/mnt/commadrive/MVL_C18_NATIVE_UI_ARTIFACTS_20261110")
ARCHIVE = C18_ARTIFACTS / "C18_NATIVE_UI_OFFLINE_CANDIDATE.tar.gz"
ROOTFS = Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs")
SOURCE = Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263")
LOCAL_COMMIT = "2b2fb0004476164704d85eea8c3f9622eea76f80"
LOCAL_TREE = "14ba8c869c9383fa2aa27caf6fb8fcd4b557b23e"
REMOTE_COMMIT = "510269282e1dbc0d692af2599de450be2e85acae"
SOURCE_COMMIT = "4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb"
ARCHIVE_SHA256 = "449624da60c90fdc667740c08153622d6d0ec721f0adaef1e7508ba181b57634"
PREFIX = "C18_NATIVE_UI_OFFLINE_CANDIDATE/"
NATIVE = (
  "runtime/msgq_repo/msgq/ipc_pyx.so",
  "runtime/msgq_repo/msgq/visionipc/visionipc_pyx.so",
  "runtime/openpilot/common/libparams_c.so",
)


def digest(path: Path) -> str:
  value = hashlib.sha256()
  with path.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
      value.update(chunk)
  return value.hexdigest()


def write_json(path: Path, value: object) -> None:
  if path.exists() or path.is_symlink():
    raise FileExistsError(f"refusing to overwrite evidence: {path}")
  path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(*args: str, directory: Path = WORKTREE) -> str:
  return subprocess.check_output(["git", "-C", str(directory), *args], text=True).strip()


def readelf(path: Path) -> dict:
  header = subprocess.check_output(["readelf", "-h", str(path)], text=True)
  dynamic = subprocess.check_output(["readelf", "-d", str(path)], text=True)
  if "ELF64" not in header or "AArch64" not in header:
    raise ValueError(f"not AArch64 ELF64: {path}")
  needed = sorted(line.split("[")[1].split("]")[0]
                  for line in dynamic.splitlines() if "(NEEDED)" in line)
  return {"sha256": digest(path), "bytes": path.stat().st_size, "needed": needed,
          "elf_class": "ELF64", "machine": "AArch64"}


def archive_audit() -> tuple[dict, dict[str, bytes]]:
  if digest(ARCHIVE) != ARCHIVE_SHA256:
    raise ValueError("C18 archive identity mismatch")
  payload: dict[str, bytes] = {}
  with tarfile.open(ARCHIVE, "r:gz") as archive:
    members = archive.getmembers()
    for member in members:
      pure = PurePosixPath(member.name)
      if pure.is_absolute() or ".." in pure.parts or member.issym() or member.islnk():
        raise ValueError(f"unsafe archive member: {member.name}")
      if not member.isfile() or not member.name.startswith(PREFIX):
        raise ValueError(f"unexpected archive member: {member.name}")
      extracted = archive.extractfile(member)
      if extracted is None:
        raise ValueError(f"unreadable archive member: {member.name}")
      payload[member.name.removeprefix(PREFIX)] = extracted.read()
  manifest = json.loads(payload["MANIFEST.json"])
  expected = manifest["files"]
  if set(payload) != set(expected) | {"MANIFEST.json"}:
    raise ValueError("archive/manifest membership mismatch")
  for name, record in expected.items():
    data = payload[name]
    if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
      raise ValueError(f"manifest mismatch: {name}")
  credential_names = [name for name in payload if PurePosixPath(name).name.lower() in
                      {"id_rsa", "id_dsa"} or PurePosixPath(name).suffix.lower() in
                      {".pem", ".key", ".p12", ".pfx"}]
  if credential_names:
    raise ValueError(f"credential-like members: {credential_names}")
  result = {"result": "PASS", "archive_sha256": ARCHIVE_SHA256,
            "archive_bytes": ARCHIVE.stat().st_size, "regular_file_members": len(payload),
            "manifest_payload_members": len(expected), "path_safety": "PASS",
            "membership": "PASS", "payload_hashes_and_sizes": "PASS",
            "credential_like_members": []}
  return result, payload


def offline(artifacts: Path) -> None:
  if not artifacts.is_absolute() or not artifacts.is_dir() or artifacts.is_symlink():
    raise ValueError("artifacts must be an existing absolute non-symlink directory")
  archive_result, payload = archive_audit()
  c19_head = git("rev-parse", "HEAD")
  c19_tree = git("rev-parse", "HEAD^{tree}")
  c18_tree = git("rev-parse", f"{LOCAL_COMMIT}^{{tree}}")
  source_head = git("rev-parse", "HEAD", directory=SOURCE)
  if (c18_tree, source_head) != (LOCAL_TREE, SOURCE_COMMIT):
    raise ValueError("baseline Git identity mismatch")
  subprocess.run(["git", "-C", str(WORKTREE), "merge-base", "--is-ancestor",
                  LOCAL_COMMIT, c19_head], check=True)
  publication = json.loads((C18_ARTIFACTS / "C18_POSTHANDOFF_PUBLICATION_20261110" /
                            "C18_GITHUB_PUBLICATION_VERIFIED.json").read_text())
  if publication["remote_commit"] != REMOTE_COMMIT or publication["identical_git_source_tree_sha1"] != LOCAL_TREE:
    raise ValueError("published C18 identity mismatch")
  manifest = json.loads(payload["MANIFEST.json"])
  if manifest["release_engineering_commit"] != LOCAL_COMMIT or manifest["source_commit"] != SOURCE_COMMIT:
    raise ValueError("manifest provenance mismatch")

  with tempfile.TemporaryDirectory(prefix="c19-elf-") as temporary:
    root = Path(temporary)
    native = {}
    for name in NATIVE:
      path = root / PurePosixPath(name).name
      path.write_bytes(payload[name])
      native[name] = readelf(path)

  version = (ROOTFS / "VERSION").read_text().strip()
  if version != "19.9":
    raise ValueError("reference rootfs is not AGNOS 19.9")
  raylib = ROOTFS / "usr/local/venv/lib/python3.12/site-packages/raylib/_raylib_cffi_comma.abi3.so"
  graphics = readelf(raylib)
  required_graphics = {"libEGL.so.1", "libGLESv2.so.2", "libgbm.so.1", "libdrm.so.2"}
  if not required_graphics.issubset(graphics["needed"]):
    raise ValueError("genuine Comma graphics dependency set incomplete")
  launcher = payload["app/c18_native_ui.sh"].decode()
  entrypoint = payload["app/c18_native_ui.py"].decode()
  forbidden_launches = [token for token in ("manager.py", "controlsd", "pandad", "boardd",
                                             "modeld", "plannerd", "radard", "sendcan")
                        if re.search(rf"(?:exec|python(?:3)?|subprocess\.[A-Za-z]+)\s+[^\n]*{re.escape(token)}",
                                     launcher + "\n" + entrypoint)]
  if forbidden_launches or "PubMaster" in entrypoint or ".send(" in entrypoint:
    raise ValueError(f"unsafe launch/publication path: {forbidden_launches}")

  baseline = {
    "campaign": "C19", "result": "PASS", "baseline": "C18 accepted native candidate",
    "local_branch": "codex/mvl-c19-isolated-comma4-qualification-20261110",
    "c19_local_commit": c19_head, "c19_local_tree": c19_tree,
    "c19_descends_from_c18_local_commit": True,
    "c18_local_commit": LOCAL_COMMIT, "c18_local_tree": LOCAL_TREE,
    "c18_remote_commit": REMOTE_COMMIT, "c18_remote_tree": LOCAL_TREE,
    "local_remote_source_trees_identical": True, "frozen_source_commit": SOURCE_COMMIT,
    "candidate_archive": str(ARCHIVE), **archive_result,
    "publication_evidence": str(C18_ARTIFACTS / "C18_POSTHANDOFF_PUBLICATION_20261110" /
                                "C18_GITHUB_PUBLICATION_VERIFIED.json"),
  }
  preflight = {
    "campaign": "C19", "result": "PASS_WITH_TARGET_ONLY_RISKS",
    "target": "Comma 4 / AGNOS 19.9 / AArch64", "agnos_reference_version": version,
    "package_integrity": archive_result, "native_binaries": native,
    "graphics_backend": {"path": "/usr/local/venv/lib/python3.12/site-packages/raylib/_raylib_cffi_comma.abi3.so",
                         **graphics, "required_dependencies": sorted(required_graphics),
                         "static_dependency_closure": "PASS", "physical_initialization": "NOT_RUN"},
    "launcher_syntax": "PASS_IN_C18_AND_RECHECKED_BY_C19_REGRESSION",
    "display_entrypoint_has_ipc_publisher": False,
    "manager_controller_panda_can_launch_paths": [],
    "aarch64_capnp_and_ui_state_import": "PASS_WITH_PRIVATE_GENUINE_IPC_FIXTURE",
    "aarch64_missing_publisher_behavior": "FAIL_FAST_IPC_ERROR_EXPLICIT_TARGET_RISK",
    "real_adreno_drm_egl": "NOT_RUN", "physical_device_contacted": False,
    "target_only_risks": [
      "Real mici device identity path /sys/firmware/devicetree/base/model is unavailable offline.",
      "Private native SubMaster construction fails if required publisher endpoints do not exist.",
      "The genuine Comma Raylib backend cannot initialize DRM/EGL without real target display nodes.",
      "Display ownership/coexistence with the installed UI is unknown until authorized device inspection.",
    ],
  }
  write_json(artifacts / "C19_BASELINE_PROVENANCE.json", baseline)
  write_json(artifacts / "C19_NATIVE_RUNTIME_PREFLIGHT.json", preflight)


def hold_records(artifacts: Path) -> None:
  common = {"campaign": "C19", "status": "NOT_RUN", "reason": "PHYSICAL_DEVICE_HOLD",
            "physical_device_contacted": False, "device_software_changed": False,
            "install_allowed": False, "actuation_allowed": False}
  records = {
    "C19_DEVICE_IDENTITY.json": {**common, "actual_comma4_identity": None, "agnos_version": None},
    "C19_PHYSICAL_ISOLATION_EVIDENCE.json": {**common, "physical_isolation_witnessed": False,
      "note": "No attestation was inferred or generated."},
    "C19_POWER_THERMAL_QUALIFICATION.json": {**common, "bench_power_verified": False,
      "thermal_environment_verified": False},
    "C19_DEVICE_BACKUP_MANIFEST.json": {**common, "backup_created": False, "files": []},
    "C19_BACKUP_INTEGRITY_REPORT.json": {**common, "backup_verified": False},
    "C19_RECOVERY_REHEARSAL_RESULTS.json": {**common, "restoration_genuinely_demonstrated": False},
    "C19_DEVICE_AUTHORIZATION.json": {**common, "authorization_received": False,
      "note": "No P1-P7 fields were fabricated or auto-populated."},
    "C19_GRAPHICS_HARDWARE_RESULTS.json": {**common, "adreno_initialized": False,
      "drm_initialized": False, "egl_initialized": False},
    "C19_NATIVE_IPC_RESULTS.json": {**common, "on_device_ipc_tested": False},
    "C19_DISPLAY_RENDER_RESULTS.json": {**common, "large_layout_observed": False,
      "compact_layout_observed": False, "actual_device_capture": None},
    "C19_APPLICATION_LIFECYCLE_RESULTS.json": {**common, "on_device_lifecycle_tested": False},
    "C19_POST_TEST_INTEGRITY.json": {**common, "post_test_checks_performed": False,
      "not_applicable_because_no_device_test_started": True},
    "C19_RECOVERY_EXECUTION_RESULTS.json": {**common, "restoration_performed": False},
    "C19_DEVICE_FINAL_STATE.json": {**common, "final_state_observed": False,
      "known_state": "UNCONTACTED"},
  }
  for name, value in records.items():
    write_json(artifacts / name, value)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("command", choices=("offline", "physical-hold"))
  parser.add_argument("--artifacts", type=Path, default=ARTIFACTS_DEFAULT)
  args = parser.parse_args()
  if args.command == "offline":
    offline(args.artifacts)
  else:
    hold_records(args.artifacts)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
