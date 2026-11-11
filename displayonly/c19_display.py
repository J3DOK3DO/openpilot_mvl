#!/usr/bin/env python3
"""Read-only MVL-StarPilot R3 dashboard for a clean AGNOS 19.9 install."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import time

MODULE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIR))
from layout import PALETTE, commands, validate  # noqa: E402

# Mandatory visible safety semantics rendered by both layouts:
# DISPLAY ONLY / DISCONNECTED / NO VEHICLE DATA / ACTUATION DISABLED.


def deny(*_args, **_kwargs):
  raise RuntimeError("R3_DISPLAY_ONLY_FORBIDS_PROCESS_OR_NETWORK")


def install_guards() -> None:
  subprocess.Popen = deny
  subprocess.run = deny
  subprocess.call = deny
  os.system = deny
  original_connect = socket.socket.connect

  def local_only(sock, address):
    if sock.family != socket.AF_UNIX:
      raise RuntimeError("R3_DISPLAY_ONLY_FORBIDS_NONLOCAL_NETWORK")
    return original_connect(sock, address)

  socket.socket.connect = local_only


def atomic_json(path: Path, value: dict) -> None:
  temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
  with temporary.open("x", encoding="utf-8") as stream:
    json.dump(value, stream, indent=2, sort_keys=True)
    stream.write("\n")
    stream.flush()
    os.fsync(stream.fileno())
  os.replace(temporary, path)


def draw(rl, layout: str, demo: bool) -> None:
  _, items = commands(layout, demo)
  for item in items:
    x, y, width, height = item.bounds
    color = rl.Color(*PALETTE[item.color])
    if item.kind == "rect":
      rl.draw_rectangle(x, y, width, height, color)
    elif item.kind == "line":
      rl.draw_line(x, y, x + width, y + height, color)
    elif item.kind == "circle":
      rl.draw_circle(x + width // 2, y + height // 2, width / 2, color)
    elif item.kind == "text":
      measured = rl.measure_text(item.text, item.size)
      if measured > width:
        raise RuntimeError(f"rendered text clips: {item.text}")
      text_x = x if item.align == "left" else x + width - measured
      if item.align == "center":
        text_x = x + (width - measured) // 2
      rl.draw_text(item.text, text_x, y + max(0, (height - item.size) // 2), item.size, color)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--layout", choices=("auto", "large", "compact"), default="auto")
  parser.add_argument("--demo", action="store_true", help="qualification-only static fixture")
  parser.add_argument("--ready", type=Path, required=True)
  parser.add_argument("--status", type=Path, required=True)
  parser.add_argument("--max-frames", type=int, default=0,
                      help="qualification only; zero runs until signalled")
  args = parser.parse_args()
  if not 0 <= args.max_frames <= 36000:
    parser.error("max-frames must be in [0, 36000]")
  for path in (args.ready, args.status):
    if not path.is_absolute() or path.exists() or path.is_symlink():
      raise RuntimeError("ready/status must be new absolute paths")
  runtime = Path(os.environ.get("R3_RUNTIME_DIR", ""))
  if not runtime.is_absolute() or runtime.is_symlink() or not runtime.is_dir():
    raise RuntimeError("private runtime directory required")
  if not args.ready.parent.samefile(runtime) or not args.status.parent.samefile(runtime):
    raise RuntimeError("ready/status must be confined to private runtime")

  model_path = Path("/sys/firmware/devicetree/base/model")
  physical = Path("/AGNOS").exists() and model_path.is_file()
  if physical:
    if args.demo:
      raise RuntimeError("demo is forbidden in production")
    if platform.machine() not in ("aarch64", "arm64"):
      raise RuntimeError("AGNOS execution requires AArch64")
    if Path("/VERSION").read_text(encoding="utf-8").strip() != "19.9":
      raise RuntimeError("unsupported AGNOS version")
    if b"mici" not in model_path.read_bytes().lower():
      raise RuntimeError("unsupported device identity; Comma 4 MICI required")
    if not Path("/tmp/drmfd.sock").is_socket() or not Path("/dev/dri/card0").exists():
      raise RuntimeError("Comma display ownership is unavailable")
    if os.environ.get("RAYLIB_BACKEND") != "comma":
      raise RuntimeError("genuine Comma Raylib backend required")
  elif os.environ.get("R3_OFFLINE_QUALIFICATION") != "1":
    raise RuntimeError("non-AGNOS execution is qualification-only")

  layout = "compact" if args.layout == "auto" else args.layout
  if physical and layout != "compact":
    raise RuntimeError("MICI production requires native compact layout")
  layout_errors = validate(layout, args.demo)
  if layout_errors:
    raise RuntimeError("invalid layout: " + "; ".join(layout_errors))

  install_guards()
  import pyray as rl
  dimensions, _ = commands(layout, args.demo)
  stopped = False
  stop_name = None

  def stop(sig, _frame):
    nonlocal stopped, stop_name
    stopped = True
    stop_name = signal.Signals(sig).name

  for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    signal.signal(sig, stop)

  frames = 0
  started = time.monotonic()
  close_reason = "window_close"
  rl.set_config_flags(rl.ConfigFlags.FLAG_MSAA_4X_HINT)
  rl.init_window(*dimensions, "MVL-StarPilot Display Only")
  if (rl.get_screen_width(), rl.get_screen_height()) != dimensions:
    rl.close_window()
    raise RuntimeError("native display dimensions do not match selected layout")
  rl.set_target_fps(30 if physical else 20)
  try:
    while not stopped and not rl.window_should_close():
      rl.begin_drawing()
      draw(rl, layout, args.demo)
      rl.end_drawing()
      frames += 1
      if frames == 1:
        atomic_json(args.ready, {
          "schema": "r3-display-ready-v1", "layout": layout,
          "dimensions": list(dimensions), "mode": "DEMO_OFFLINE" if args.demo else "DISCONNECTED",
          "physical_graphics_claim": False, "vehicle_data": "NONE",
          "actuation_allowed": False,
        })
      if args.max_frames and frames >= args.max_frames:
        close_reason = "bounded_frames"
        break
    if stopped:
      close_reason = f"signal:{stop_name}"
  finally:
    rl.close_window()

  atomic_json(args.status, {
    "schema": "r3-display-exit-v1", "layout": layout, "dimensions": list(dimensions),
    "mode": "DEMO_OFFLINE" if args.demo else "DISCONNECTED",
    "frames_rendered": frames, "close_reason": close_reason,
    "runtime_seconds": round(time.monotonic() - started, 3),
    "vehicle_data": "NONE", "publishers_started": [], "network_allowed": False,
    "panda_can_controls_started": False, "actuation_allowed": False,
    "physical_graphics_claim": False,
  })
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    print(f"R3_DISPLAY_FATAL {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    raise
