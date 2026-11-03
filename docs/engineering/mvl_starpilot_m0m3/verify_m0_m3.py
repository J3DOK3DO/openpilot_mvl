#!/usr/bin/env python3
"""Read-only M0–M3 source boundary verifier; no native vehicle access."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "376c44b5731b2655e5c2f301b73c9729eb499e91"
PKG = ROOT / "openpilot/sunnypilot/starpilot_bridge"
EVIDENCE = Path(__file__).resolve().parent
ALLOWED = ("openpilot/sunnypilot/starpilot_bridge/", "docs/engineering/mvl_starpilot_m0m3/")


def git(*args: str) -> str:
  return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def main() -> None:
  assert git("merge-base", "HEAD", BASE) == BASE
  paths = set(git("diff", "--name-only", BASE).splitlines())
  paths |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
  paths.discard("")
  bad_paths = sorted(p for p in paths if not p.startswith(ALLOWED))
  modules = sorted(p for p in PKG.glob("*.py"))
  assert len(modules) >= 5, len(modules)
  forbidden_import_roots = {"os", "subprocess", "socket", "requests", "urllib", "panda", "ctypes"}
  forbidden_source_tokens = {"PubMaster", "sendcan", "Params.put", "disable_ecu", "uds."}
  module_hashes = {}
  offenses = []
  for module in modules:
    source = module.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imports += [a.name for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names]
    bad_imports = [x for x in imports if x.split(".")[0] in forbidden_import_roots]
    bad_tokens = [x for x in forbidden_source_tokens if x in source]
    if bad_imports or bad_tokens:
      offenses.append({"module": module.name, "imports": bad_imports, "tokens": bad_tokens})
    module_hashes[module.name] = hashlib.sha256(module.read_bytes()).hexdigest()
  with (EVIDENCE / "SHARED_PARAMS_QUARANTINE_254.csv").open(encoding="utf-8-sig",newline="") as f:
    rows = list(csv.DictReader(f))
  assert len(rows) == 254, len(rows)
  bad_keys = [r["Key"] for r in rows if (r["ProposedImport"],r["ReadEnabled"],r["WriteEnabled"]) != ("DENY","FALSE","FALSE")]
  assert not bad_keys, bad_keys[:5]
  assert not bad_paths, bad_paths
  assert not offenses, offenses
  summary = {
    "source_head": git("rev-parse", "HEAD"),
    "protected_mvl_baseline": BASE,
    "native_opendbc_gitlink": git("rev-parse", "HEAD:opendbc_repo"),
    "native_panda_gitlink": git("rev-parse", "HEAD:panda"),
    "status": "SOURCE_BOUNDARY_PASS",
    "all_new_paths_within_allowlist": not bad_paths,
    "compiled_python_modules": len(modules),
    "privileged_source_offenses": offenses,
    "settings_quarantined": len(rows),
    "module_sha256": module_hashes,
    "not_qualified": ["vehicle", "Panda hardware", "AGNOS ARM64", "OEM AEB/CMBS", "release install"],
  }
  (EVIDENCE / "M3_STATIC_BOUNDARY_VERIFICATION.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
  print(json.dumps({k:v for k,v in summary.items() if k != "module_sha256"},indent=2))


if __name__ == "__main__":
  main()
