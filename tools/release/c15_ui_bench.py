"""Campaign 15: read-only, fail-closed audit of the isolated MVL UI engineering evidence.

No installer, device operation, control-daemon launch, model bypass, firmware or CAN action.
The only optional write is one new manifest file in the dedicated C15 evidence directory.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct
import subprocess

SOURCE_SHA = "4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb"
C13_SHA = "70e0d3e7874d764aac08d6275b8f73adb03aa8e4"
ARTIFACTS = Path("/mnt/commadrive/MVL_C15_STANDALONE_UI_BENCH_ARTIFACTS_20261110")
ARM_SOURCE = Path("/mnt/commadrive/MVL_C14A_NATIVE_IPC_WORK_20261110")
HOST_SOURCE = Path("/mnt/commadrive/MVL_C15_HOST_UI_SOURCE_20261110")
FROZEN_SOURCE = Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263")
C13_SOURCE = Path("/mnt/commadrive/MVL_C13_OPTIONA_UI_OFFLINE_20261110")
ROOTFS = Path("/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs")
NATIVE = ("msgq_repo/msgq/ipc_pyx.so",
          "msgq_repo/msgq/visionipc/visionipc_pyx.so",
          "openpilot/common/libparams_c.so")
PASS_EXIT_FILES = (
    "C15_AGNOS_CLEAN_ENV_REBUILD.exit",
    "C15_LIVE_PRIVATE_IPC_V3.exit",
    "C15_ACTUAL_UI_LIVE_IPC.exit",
    "C15_HOST_NATIVE_SCONS.exit",
    "C15_MVL_LARGE_LOOP.exit",
    "C15_MVL_COMPACT_FULL_FRAME.exit",
)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()

def git_clean(path: Path) -> bool:
    return subprocess.check_output(["git", "-C", str(path), "status", "--porcelain"], text=True).strip() == ""

def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or not header.startswith(b"\x89PNG\r\n\x1a\n") or header[12:16] != b"IHDR":
        raise ValueError(f"Not a supported PNG: {path}")
    return struct.unpack(">II", header[16:24])

def evidence() -> dict:
    for source, sha in ((ARM_SOURCE, SOURCE_SHA), (HOST_SOURCE, SOURCE_SHA),
                        (FROZEN_SOURCE, SOURCE_SHA), (C13_SOURCE, C13_SHA)):
        if git_head(source) != sha or not git_clean(source):
            raise ValueError(f"Unexpected source identity or dirty source: {source}")
    if (ROOTFS / "VERSION").read_text().strip() != "19.9":
        raise ValueError("AGNOS 19.9 mismatch")
    exits = {}
    for name in PASS_EXIT_FILES:
        code = int((ARTIFACTS / name).read_text().strip())
        if code != 0:
            raise ValueError(f"Required proof did not exit successfully: {name}: {code}")
        exits[name] = code
    required_lines = {
        "C15_LIVE_PRIVATE_IPC_V3.log": "C15_LIVE_IPC_PASS",
        "C15_ACTUAL_UI_LIVE_IPC.log": "C15_UI_LIVE_IPC_IMPORT_PASS",
        "C15_MVL_LARGE_LOOP.log": "C15_REAL_MVL_FRAMES_RENDERED 12",
        "C15_MVL_COMPACT_FULL_FRAME.log": "C15_MVL_HOST_UI_FRAME_PASS",
        "C15_AGNOS_CLEAN_ENV_REBUILD.log": "scons: done building targets.",
        "C15_HOST_NATIVE_SCONS.log": "scons: done building targets.",
    }
    for name, marker in required_lines.items():
        if marker not in (ARTIFACTS / name).read_text():
            raise ValueError(f"Missing expected real execution evidence: {name}")
    if "could not open '/dev/null'" in (ARTIFACTS / "C15_AGNOS_CLEAN_ENV_REBUILD.log").read_text():
        raise ValueError("AGNOS null-device regression")
    binaries = []
    for rel in NATIVE:
        for arch, root in (("aarch64", ARM_SOURCE), ("x86_64", HOST_SOURCE)):
            p = root / rel
            if not p.is_file() or p.stat().st_size < 20480:
                raise ValueError(f"Missing genuine native library: {p}")
            header = subprocess.check_output(["readelf", "-h", str(p)], text=True)
            machine = "AArch64" if arch == "aarch64" else "Advanced Micro Devices X86-64"
            if machine not in header or "ELF64" not in header:
                raise ValueError(f"Incorrect ABI: {p}")
            binaries.append({"target":rel, "abi":arch, "sha256":sha256(p),
                             "size_bytes":p.stat().st_size})
    # Render geometry depends on the reviewed font assets; enforce equal
    # tracked font bytes in the host-rendered, ARM build and frozen sources.
    font_dir = "openpilot/selfdrive/assets/fonts/"
    tracked = subprocess.check_output(
        ["git", "-C", str(FROZEN_SOURCE), "ls-files", "--", font_dir], text=True
    ).splitlines()
    if len(tracked) < 12 or any(not n.startswith(font_dir) for n in tracked):
        raise ValueError("Missing tracked MVL font bundle")
    fonts = []
    for rel in tracked:
        origin = FROZEN_SOURCE / rel
        if not origin.is_file() or origin.is_symlink() or origin.stat().st_size < 1024:
            raise ValueError(f"Missing/corrupted font asset: {rel}")
        expected = sha256(origin)
        for checkout in (ARM_SOURCE, HOST_SOURCE):
            current = checkout / rel
            if not current.is_file() or current.is_symlink() or sha256(current) != expected:
                raise ValueError(f"Font changed across pinned source checkouts: {rel}")
        fonts.append({"path": rel, "sha256": expected, "bytes": origin.stat().st_size})
    screenshots = []
    for name, dims in (("C15_MVL_COMPACT_FULL_HOST_FRAME.png", (536, 240)),
                       ("C15_MVL_LARGE_HOST_12FRAMES.png", (1404, 702))):
        p = ARTIFACTS / name
        if png_dimensions(p) != dims or p.stat().st_size < 20000:
            raise ValueError(f"Missing, invalid or unexpectedly small UI frame: {name}")
        screenshots.append({"name":name, "resolution":dims, "sha256":sha256(p),
                            "size_bytes":p.stat().st_size})
    # Host preview source must not contain a vehicle-control publication.
    # Note: this is static assurance of the exact executed test harness, not
    # a substitute for process isolation or live vehicular safety testing.
    preview_scripts = []
    for name in ("c15_mvl_compact_full_one_frame.py", "c15_mvl_large_loop.py"):
        p = ARTIFACTS / name
        source = p.read_text()
        tree = ast.parse(source, filename=str(p))
        sends = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "send":
                if (not node.args or not isinstance(node.args[0], ast.Constant)
                        or node.args[0].value != "deviceState"):
                    raise ValueError(f"Unexpected host preview publish call: {name}")
                sends.append("deviceState")
        if not sends or "NOBOARD" not in source or "SIMULATION" not in source:
            raise ValueError(f"Host preview boundary missing: {name}")
        preview_scripts.append({"path": name, "sha256": sha256(p), "permitted_publish_service": "deviceState",
                                "send_call_sites": len(sends)})
    egl_code = int((ARTIFACTS / "C15_EGL_PROBE.exit").read_text().strip())
    if egl_code == 0:
        raise ValueError("This checkpoint must not infer target graphics approval from the failed prior probe")
    return {"campaign": "C15_STANDALONE_UI_ENGINEERING_BENCH",
            "frozen_source_commit": SOURCE_SHA, "agnos_version": "19.9",
            "status": "HOST_UI_BENCH_PASS_AGNOS_GPU_HARDWARE_HOLD",
            "source_identities_clean": True, "source_modified": False,
            "native_module_count": 3, "native_binaries": binaries,
            "model_artifacts_authenticated": 0, "g10_full_product_built": False,
            "device_graphics_qualified": False, "agnos_software_egl_probe_exit": egl_code,
            "private_native_ipc_delivered": True, "mvl_ui_native_submaster_received": True,
            "real_host_ui_render": True, "host_large_frames_rendered": 12,
            "screenshots": screenshots, "source_font_assets_verified": fonts,
            "host_preview_scripts_verified": preview_scripts,
            "physical_comma_tested": False, "device_install_allowed": False,
            "actuation_allowed": False, "panda_flashing_allowed": False,
            "vehicle_can_transmission": False, "option_b_qualified": False,
            "evidence_exit_codes": exits,
            "review_status": "INDEPENDENT_REVIEW_PENDING",
            "next_gate": "Physical isolated Comma 4 GPU/display and rollback acceptance",
            "scope": "Offline native binaries, private live IPC, nonactuating host UI rendering only"}

def safe_output(path: Path) -> None:
    if (ARTIFACTS.is_symlink() or not ARTIFACTS.is_dir()
            or path.parent != ARTIFACTS or path.parent.resolve() != ARTIFACTS.resolve()
            or not path.is_absolute() or path.exists() or path.is_symlink() or ".." in path.parts):
        raise ValueError("Only a new direct file in the C15 artifacts directory is allowed")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evidence()
    print(json.dumps(report, indent=2))
    if args.output is not None:
        safe_output(args.output)
        with args.output.open("x") as fp:
            json.dump(report, fp, indent=2)
            fp.write("\n")

if __name__ == "__main__":
    main()
