#!/usr/bin/env python3
"""Non-actuating MVL-StarPilot dashboard for a clean AGNOS 19.9 install."""
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


def deny(*_args, **_kwargs):
  raise RuntimeError("C19_DISPLAY_ONLY_FORBIDS_PROCESS_OR_NETWORK")


def install_guards() -> None:
  subprocess.Popen = deny
  subprocess.run = deny
  subprocess.call = deny
  os.system = deny
  original_connect = socket.socket.connect

  def local_only(sock, address):
    if sock.family != socket.AF_UNIX:
      raise RuntimeError("C19_DISPLAY_ONLY_FORBIDS_NONLOCAL_NETWORK")
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


def centered(rl, text: str, y: int, size: int, color) -> None:
  width = rl.measure_text(text, size)
  rl.draw_text(text, (rl.get_screen_width() - width) // 2, y, size, color)


def draw_dashboard(rl, compact: bool) -> None:
  width = rl.get_screen_width()
  height = rl.get_screen_height()
  accent = rl.Color(42, 205, 125, 255)
  warning = rl.Color(255, 181, 46, 255)
  muted = rl.Color(165, 174, 185, 255)
  panel = rl.Color(22, 28, 36, 255)
  rl.clear_background(rl.Color(8, 12, 18, 255))

  if compact:
    rl.draw_rectangle(0, 0, width, 42, panel)
    rl.draw_circle(24, 21, 7, accent)
    rl.draw_text("MVL-STARPILOT", 42, 10, 20, rl.RAYWHITE)
    rl.draw_text("DISPLAY ONLY", width - 150, 12, 16, accent)
    centered(rl, "--", 56, 92, rl.RAYWHITE)
    centered(rl, "NO VEHICLE DATA", 151, 21, warning)
    centered(rl, "DISCONNECTED  |  ACTUATION DISABLED", 190, 16, muted)
  else:
    rl.draw_rectangle(0, 0, width, 118, panel)
    rl.draw_circle(66, 59, 18, accent)
    rl.draw_text("MVL-STARPILOT", 104, 28, 54, rl.RAYWHITE)
    tag = "DISPLAY ONLY"
    rl.draw_text(tag, width - rl.measure_text(tag, 38) - 60, 39, 38, accent)
    centered(rl, "--", 185, 330, rl.RAYWHITE)
    centered(rl, "DISCONNECTED — NO VEHICLE DATA", 590, 62, warning)
    centered(rl, "ACTUATION DISABLED", 695, 54, rl.Color(238, 91, 91, 255))
    centered(rl, "No Panda • No CAN • No controls • No publishers", 810, 34, muted)
    rl.draw_rectangle(90, height - 92, width - 180, 2, rl.Color(60, 70, 82, 255))
    centered(rl, "Standalone offroad status display", height - 66, 28, muted)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--layout", choices=("auto", "large", "compact"), default="auto")
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
  runtime = Path(os.environ.get("C19_RUNTIME_DIR", ""))
  if not runtime.is_absolute() or runtime.is_symlink() or not runtime.is_dir():
    raise RuntimeError("private runtime directory required")
  if not args.ready.parent.samefile(runtime) or not args.status.parent.samefile(runtime):
    raise RuntimeError("ready/status must be confined to private runtime")

  model_path = Path("/sys/firmware/devicetree/base/model")
  physical = Path("/AGNOS").exists() and model_path.is_file()
  if physical:
    if platform.machine() not in ("aarch64", "arm64"):
      raise RuntimeError("AGNOS execution requires AArch64")
    if Path("/VERSION").read_text(encoding="utf-8").strip() != "19.9":
      raise RuntimeError("unsupported AGNOS version")
    model = model_path.read_bytes().lower()
    if b"mici" not in model:
      raise RuntimeError("unsupported device identity; Comma 4 MICI required")
    if not Path("/tmp/drmfd.sock").is_socket() or not Path("/dev/dri/card0").exists():
      raise RuntimeError("Comma display ownership is unavailable")
    if os.environ.get("RAYLIB_BACKEND") != "comma":
      raise RuntimeError("genuine Comma Raylib backend required")
  elif os.environ.get("C19_OFFLINE_QUALIFICATION") != "1":
    raise RuntimeError("non-AGNOS execution is qualification-only")

  install_guards()
  import pyray as rl

  if args.layout == "auto":
    compact = physical
  else:
    compact = args.layout == "compact"
  dimensions = (536, 240) if compact else (2160, 1080)
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
  rl.set_target_fps(30 if physical else 20)
  try:
    while not stopped and not rl.window_should_close():
      rl.begin_drawing()
      draw_dashboard(rl, compact)
      rl.end_drawing()
      frames += 1
      if frames == 1:
        atomic_json(args.ready, {
          "schema": "c19-display-ready-v1", "layout": "compact" if compact else "large",
          "physical_graphics_claim": False, "vehicle_data": "DISCONNECTED",
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
    "schema": "c19-display-exit-v1", "layout": "compact" if compact else "large",
    "frames_rendered": frames, "close_reason": close_reason,
    "runtime_seconds": round(time.monotonic() - started, 3),
    "vehicle_data": "DISCONNECTED", "publishers_started": [],
    "panda_can_controls_started": False, "actuation_allowed": False,
    "physical_graphics_claim": False,
  })
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    print(f"C19_DISPLAY_FATAL {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    raise
