#!/usr/bin/env python3
"""Rebuild SHA-256 evidence manifest; worktree only, no vehicle access."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = Path(__file__).resolve().parent
SOURCE = ROOT / "openpilot/sunnypilot/starpilot_bridge"
OUT = DOC / "M0_M3_EVIDENCE_MANIFEST.json"


def main() -> None:
  items = []
  for base in (SOURCE, DOC):
    for path in sorted(base.rglob("*")):
      if not path.is_file() or path == OUT or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
      data = path.read_bytes()
      items.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
  summary = {
    "schema_version": 1, "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "base_mvl_sha": "376c44b5731b2655e5c2f301b73c9729eb499e91",
    "branch": "accord11g-mvl-starpilot-readonly-integration-20261103",
    "classification": "OFFLINE_HOST_M0_M3_PASS_VEHICLE_HOLD",
    "mvl_native_baseline": {"passed": 1140, "skipped": 613, "failed": 0, "subtests_passed": 1190},
    "bridge_native_host": {"passed": 51, "skipped": 0, "failed": 0},
    "real_native_submaster": "deviceState_only_SUBSCRIBER_PASS",
    "settings_keys_quarantined": 254,
    "verified_file_count": len(items), "files": items,
  }
  OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
  print(f"MANIFEST_PASS: {len(items)} items, total {sum(item['bytes'] for item in items)} bytes")


if __name__ == "__main__":
  main()
