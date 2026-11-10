#!/usr/bin/env python3
"""Render the authentic MVL offroad UI in the isolated C17 host bench."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time


def _deny_process(*_args, **_kwargs):
  raise RuntimeError("C17_BENCH_FORBIDS_PROCESS_LAUNCH")


def _install_guards() -> None:
  subprocess.Popen = _deny_process
  os.system = _deny_process
  original_connect = socket.socket.connect

  def guarded_connect(sock, address):
    if sock.family != socket.AF_UNIX:
      raise RuntimeError("C17_BENCH_FORBIDS_NETWORK")
    return original_connect(sock, address)

  socket.socket.connect = guarded_connect
  try:
    import requests
    requests.sessions.Session.request = _deny_process
  except ImportError:
    pass


def _exclusive_json(path: Path, data: dict) -> None:
  with path.open("x", encoding="utf-8") as stream:
    json.dump(data, stream, indent=2, sort_keys=True)
    stream.write("\n")


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--layout", choices=("large", "compact"), required=True)
  parser.add_argument("--frames", type=int, default=12)
  parser.add_argument("--output-dir", type=Path, required=True)
  parser.add_argument("--params-mode", choices=("normal", "empty", "malformed"), default="normal")
  parser.add_argument("--publisher", choices=("required", "optional"), default="required")
  parser.add_argument("--publisher-mode", choices=("continuous", "terminate", "absent"), required=True)
  args = parser.parse_args()
  if not 1 <= args.frames <= 600:
    parser.error("frames must be in [1, 600]")
  if not args.output_dir.is_absolute() or not args.output_dir.is_dir() or args.output_dir.is_symlink():
    raise RuntimeError("output-dir must be an existing absolute non-symlink directory")

  required_env = {
    "C17_BENCH_TOKEN": "display-only",
    "NOBOARD": "1",
    "SIMULATION": "1",
    "RAYLIB_BACKEND": "desktop",
    "RECORD": "0",
  }
  for key, expected in required_env.items():
    if os.environ.get(key) != expected:
      raise RuntimeError(f"unsafe or missing environment: {key}")
  for key in ("OPENPILOT_PREFIX", "PARAMS_ROOT", "HOME", "DISPLAY"):
    if not os.environ.get(key):
      raise RuntimeError(f"missing private environment: {key}")
  for target in (args.output_dir / "result.json", args.output_dir / "frame.png"):
    if target.exists() or target.is_symlink():
      raise FileExistsError(f"refusing overwrite: {target}")
  os.chdir(args.output_dir)

  _install_guards()
  from openpilot.common.params import Params

  params = Params()
  if args.params_mode == "normal":
    from openpilot.common.version import (sunnylink_consent_version, terms_version,
                                          terms_version_sp, training_version)
    for key, value in (
      ("HasAcceptedTerms", terms_version),
      ("CompletedTrainingVersion", training_version),
      ("HasAcceptedTermsSP", terms_version_sp),
      ("CompletedSunnylinkConsentVersion", sunnylink_consent_version),
      ("Version", "C17 isolated host bench"),
      ("GitBranch", "NON_INSTALLABLE_HOST_BENCH"),
      ("GitCommit", "4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb"),
    ):
      params.put(key, value, block=True)
  elif args.params_mode == "malformed":
    Path(params.get_param_path("InitialCruiseSpeedKph")).write_bytes(b"not-an-integer")

  from openpilot.selfdrive.ui.ui_state import ui_state
  from openpilot.system.ui.lib.application import gui_app
  if args.layout == "large":
    from openpilot.selfdrive.ui.layouts.main import MainLayout as Layout
  else:
    from openpilot.selfdrive.ui.mici.layouts.main import MiciMainLayout as Layout
  import pyray as rl

  stop_signal = None

  def request_stop(sig, _frame):
    nonlocal stop_signal
    stop_signal = signal.Signals(sig).name
    gui_app.request_close()

  signal.signal(signal.SIGTERM, request_stop)
  signal.signal(signal.SIGHUP, request_stop)

  ipc_seen = False
  ipc_updates = 0
  ipc_last_update = None
  deadline = time.monotonic() + 3.0
  while time.monotonic() < deadline and not ipc_seen:
    ui_state.sm.update(50)
    if ui_state.sm.updated["deviceState"]:
      ipc_updates += 1
      ipc_last_update = time.monotonic()
    ipc_seen = bool(ui_state.sm.seen["deviceState"])
  if args.publisher == "required" and not ipc_seen:
    raise RuntimeError("deviceState publisher unavailable")

  title = f"C17 MVL DISPLAY-ONLY {args.layout.upper()} HOST BENCH"
  gui_app.init_window(title, fps=20)
  frames = 0
  close_reason = "bounded_frames"
  try:
    Layout()
    renderer = gui_app.render()
    while frames < args.frames:
      ui_state.sm.update(0)
      if ui_state.sm.updated["deviceState"]:
        ipc_updates += 1
        ipc_last_update = time.monotonic()
      try:
        should_render, _frame_time, _cpu_time = next(renderer)
      except StopIteration:
        close_reason = f"signal:{stop_signal}" if stop_signal is not None else "window_manager_close"
        break
      if should_render:
        frames += 1
      if stop_signal is not None:
        close_reason = f"signal:{stop_signal}"
        break
    if frames and stop_signal is None:
      rl.take_screenshot("frame.png")
    gui_app.request_close()
    try:
      next(renderer)
    except StopIteration:
      pass
  finally:
    gui_app.close()

  screenshot = args.output_dir / "frame.png"
  if frames and stop_signal is None:
    if not screenshot.is_file() or screenshot.stat().st_size < 4096:
      raise RuntimeError("render completed without a valid screenshot")
    screenshot_sha256 = hashlib.sha256(screenshot.read_bytes()).hexdigest()
  else:
    screenshot_sha256 = None
  ipc_age = None if ipc_last_update is None else max(0.0, time.monotonic() - ipc_last_update)
  ipc_fresh = ipc_age is not None and ipc_age <= 0.5
  if args.publisher_mode == "absent":
    ipc_health = "DEGRADED_NO_PUBLISHER"
  elif args.publisher_mode == "terminate":
    ipc_health = ("DEGRADED_PUBLISHER_TERMINATED_RECENT_BUFFER" if ipc_fresh
                  else "DEGRADED_PUBLISHER_TERMINATED_STALE")
  else:
    ipc_health = "HOST_FIXTURE_CONTINUOUS_FRESH" if ipc_fresh else "DEGRADED_CONTINUOUS_STALE"
  result = {
    "campaign": "C17",
    "close_reason": close_reason,
    "device_state_seen_by_real_ui_submaster": ipc_seen,
    "device_state_update_count": ipc_updates,
    "frames_rendered": frames,
    "layout": args.layout,
    "params_mode": args.params_mode,
    "publisher_requirement": args.publisher,
    "publisher_mode": args.publisher_mode,
    "ipc_health": ipc_health,
    "ipc_fresh_at_exit": ipc_fresh,
    "ipc_last_update_age_seconds": None if ipc_age is None else round(ipc_age, 3),
    "ipc_health_scope": "isolated synthetic host fixture only; never device publisher qualification",
    "screenshot_sha256": screenshot_sha256,
    "source_commit": "4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb",
    "synthetic_device_state_only": True,
    "vehicle_or_control_messages": False,
  }
  _exclusive_json(args.output_dir / "result.json", result)
  print("C17_UI_RESULT " + json.dumps(result, sort_keys=True), flush=True)
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    print(f"C17_UI_FAIL {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    raise
