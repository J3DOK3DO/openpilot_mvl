#!/usr/bin/env python3
"""C17 isolated fixture: publish synthetic offroad deviceState only."""
from __future__ import annotations

import argparse
import os
import signal
import time


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--messages", type=int, default=0,
                      help="Exit after N messages; 0 continues until signalled")
  parser.add_argument("--hz", type=float, default=20.0)
  args = parser.parse_args()
  if args.messages < 0 or not 1 <= args.hz <= 100:
    parser.error("messages must be >= 0 and hz must be in [1, 100]")

  required = ("OPENPILOT_PREFIX", "PARAMS_ROOT", "C17_BENCH_TOKEN")
  if any(not os.environ.get(key) for key in required):
    raise RuntimeError("C17 private runtime environment is incomplete")

  from openpilot.cereal import messaging

  stop = False

  def request_stop(_sig, _frame):
    nonlocal stop
    stop = True

  signal.signal(signal.SIGINT, request_stop)
  signal.signal(signal.SIGTERM, request_stop)
  pm = messaging.PubMaster(["deviceState"])
  count = 0
  period = 1.0 / args.hz
  while not stop and (args.messages == 0 or count < args.messages):
    msg = messaging.new_message("deviceState")
    msg.valid = True
    msg.deviceState.started = False
    pm.send("deviceState", msg)
    count += 1
    time.sleep(period)
  print(f"C17_PUBLISHER_EXIT messages={count} service=deviceState started=false", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
