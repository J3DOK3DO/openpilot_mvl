#!/usr/bin/env python3
"""Bounded, non-actuating MVL UI entrypoint for an isolated Comma 4."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time


def _deny(*_args, **_kwargs):
  raise RuntimeError("C18_DISPLAY_APP_FORBIDS_PROCESS_OR_NETWORK")


def install_guards() -> None:
  subprocess.Popen = _deny
  os.system = _deny
  original_connect = socket.socket.connect

  def local_only(sock, address):
    if sock.family != socket.AF_UNIX:
      raise RuntimeError("C18_DISPLAY_APP_FORBIDS_NETWORK")
    return original_connect(sock, address)

  socket.socket.connect = local_only


def write_status(path: Path, data: dict) -> None:
  temporary = path.with_name(f".{path.name}.tmp")
  with temporary.open("x", encoding="utf-8") as stream:
    json.dump(data, stream, indent=2, sort_keys=True)
    stream.write("\n")
    stream.flush()
    os.fsync(stream.fileno())
  os.replace(temporary, path)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--layout", choices=("auto", "large", "compact"), default="auto")
  parser.add_argument("--max-frames", type=int, default=0,
                      help="0 runs until signalled; nonzero is for approved bounded qualification")
  parser.add_argument("--status", type=Path, required=True)
  args = parser.parse_args()
  if not 0 <= args.max_frames <= 36000:
    parser.error("max-frames must be in [0, 36000]")
  if not args.status.is_absolute() or args.status.exists() or args.status.is_symlink():
    raise RuntimeError("status must be a new absolute path")

  required = {"C18_DISPLAY_ONLY": "1", "NOBOARD": "1", "RECORD": "0",
              "RAYLIB_BACKEND": "comma"}
  for key, expected in required.items():
    if os.environ.get(key) != expected:
      raise RuntimeError(f"unsafe or missing environment: {key}")
  if not os.environ.get("OPENPILOT_PREFIX", "").startswith("c18_display_"):
    raise RuntimeError("isolated OPENPILOT_PREFIX required")
  if not os.environ.get("PARAMS_ROOT"):
    raise RuntimeError("isolated PARAMS_ROOT required")

  install_guards()
  from openpilot.selfdrive.ui.ui_state import ui_state
  from openpilot.system.ui.lib.application import gui_app
  if args.layout == "large" or (args.layout == "auto" and gui_app.big_ui()):
    from openpilot.selfdrive.ui.layouts.main import MainLayout as Layout
    layout = "large"
  else:
    from openpilot.selfdrive.ui.mici.layouts.main import MiciMainLayout as Layout
    layout = "compact"

  stop_signal = None

  def stop(sig, _frame):
    nonlocal stop_signal
    stop_signal = signal.Signals(sig).name
    gui_app.request_close()

  signal.signal(signal.SIGTERM, stop)
  signal.signal(signal.SIGINT, stop)
  signal.signal(signal.SIGHUP, stop)
  started = time.monotonic()
  frames = updates = 0
  last_update = None
  close_reason = "window_close"
  gui_app.init_window("MVL StarPilot Display Only", fps=20)
  try:
    Layout()
    for should_render, _frame_time, _cpu_time in gui_app.render():
      ui_state.sm.update(0)
      if ui_state.sm.updated["deviceState"]:
        updates += 1
        last_update = time.monotonic()
      if should_render:
        frames += 1
      if stop_signal is not None:
        close_reason = f"signal:{stop_signal}"
        break
      if args.max_frames and frames >= args.max_frames:
        close_reason = "bounded_frames"
        break
  finally:
    gui_app.close()

  age = None if last_update is None else max(0.0, time.monotonic() - last_update)
  fresh = age is not None and age <= 0.5
  status = {
    "campaign": "C18", "classification": "NATIVE_UI_OFFLINE_CANDIDATE",
    "layout": layout, "frames_rendered": frames, "close_reason": close_reason,
    "runtime_seconds": round(time.monotonic() - started, 3),
    "device_state_updates": updates, "device_state_fresh_at_exit": fresh,
    "device_state_age_seconds": None if age is None else round(age, 3),
    "ipc_status": "FRESH" if fresh else ("STALE" if last_update is not None else "MISSING"),
    "synthetic_hardware_claim": False, "vehicle_control_publication": False,
    "source_commit": "4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb",
  }
  write_status(args.status, status)
  print("C18_NATIVE_UI_RESULT " + json.dumps(status, sort_keys=True), flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
