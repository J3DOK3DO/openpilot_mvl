"""Command line interface for the offline semantic crosswalk tool."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .crosswalk import CrosswalkError, build_crosswalk, crosswalk_csv, inspect_literal_occurrences, load_quarantine
from .inventory import build_message_inventory


def _write(value: str, output: str | None) -> None:
  if output:
    Path(output).write_text(value, encoding="utf-8", newline="\n")
  else:
    sys.stdout.write(value)


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description="Read-only MVL/StarPilot quarantine evidence tool")
  parser.add_argument("--quarantine", type=Path, required=True)
  parser.add_argument("--params-keys", type=Path)
  sub = parser.add_subparsers(dest="command", required=True)
  render = sub.add_parser("render", help="emit a deterministic 254-key crosswalk")
  render.add_argument("--format", choices=("json", "csv"), default="json")
  render.add_argument("--output")
  inspect = sub.add_parser("inspect", help="inspect local literal occurrences for one quarantined key")
  inspect.add_argument("--mvl-root", type=Path, required=True)
  inspect.add_argument("--key", required=True)
  inspect.add_argument("--output")
  inventory = sub.add_parser("inventory", help="emit source-backed message and IPC/Cap'n Proto evidence")
  inventory.add_argument("--repository-root", type=Path, required=True)
  inventory.add_argument("--output")
  args = parser.parse_args(argv)
  try:
    if args.command == "render":
      document = build_crosswalk(args.quarantine, args.params_keys)
      value = crosswalk_csv(document) if args.format == "csv" else json.dumps(document, sort_keys=True, indent=2) + "\n"
      _write(value, args.output)
    elif args.command == "inspect":
      entries = load_quarantine(args.quarantine)
      document = {"key": args.key, "occurrences": inspect_literal_occurrences(args.mvl_root, args.key,
                  (entry.key for entry in entries)), "mode": "READ_ONLY_LITERAL_INSPECTION"}
      _write(json.dumps(document, sort_keys=True, indent=2) + "\n", args.output)
    else:
      _write(json.dumps(build_message_inventory(args.repository_root), sort_keys=True, indent=2) + "\n", args.output)
  except (CrosswalkError, OSError) as error:
    parser.error(str(error))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
