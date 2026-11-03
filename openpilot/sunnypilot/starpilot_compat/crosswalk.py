"""Pure-stdlib semantic crosswalk evidence generation.

No result produced here is an approval.  In particular, native Params metadata
is evidence about the local MVL tree, not a migration API.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

EXPECTED_COLUMNS = ("Key", "DomOccurrences", "MVLOccurrences", "DomExample", "MVLExample",
                    "ProposedImport", "ReadEnabled", "WriteEnabled", "SemanticType", "ReviewStatus",
                    "AcceptanceCriterion")
EXPECTED_COUNT = 254
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,127}$")

# These lexical signals only prioritize a human semantic review. They never grant access.
HIGH_RISK_TOKENS = (
  "honda", "car", "control", "steer", "longitudinal", "lateral", "calibration", "torque",
  "safety", "panda", "can", "ecu", "firmware", "vin", "dongle", "token", "ssh", "password",
  "auth", "access", "gps", "location", "route", "camera", "model", "driver", "dm", "enabled",
  "engaged", "decel", "cruise", "actuation",
)
LIFECYCLE_TOKENS = ("boot", "shutdown", "reboot", "uninstall", "update", "manager", "pid")


class CrosswalkError(ValueError):
  """A source artifact is malformed or an inspection request is unsafe."""


@dataclass(frozen=True)
class QuarantineEntry:
  key: str
  dom_occurrences: int
  mvl_occurrences: int
  dom_example: str
  mvl_example: str
  acceptance_criterion: str


def _require(condition: bool, message: str) -> None:
  if not condition:
    raise CrosswalkError(message)


def load_quarantine(path: Path) -> tuple[QuarantineEntry, ...]:
  """Load the pinned CSV and enforce its complete deny-by-default contract."""
  with path.open(newline="", encoding="utf-8") as source:
    reader = csv.DictReader(source)
    _require(tuple(reader.fieldnames or ()) == EXPECTED_COLUMNS, "unexpected quarantine CSV columns")
    rows = list(reader)
  _require(len(rows) == EXPECTED_COUNT, f"expected {EXPECTED_COUNT} quarantine rows, got {len(rows)}")
  entries = []
  seen = set()
  for row in rows:
    key = row["Key"]
    _require(KEY_RE.fullmatch(key) is not None, f"unsafe quarantine key: {key!r}")
    _require(key not in seen, f"duplicate quarantine key: {key}")
    seen.add(key)
    _require(row["ProposedImport"] == "DENY", f"{key}: import must remain DENY")
    _require(row["ReadEnabled"] == "FALSE" and row["WriteEnabled"] == "FALSE",
             f"{key}: reads and writes must remain disabled")
    _require(row["SemanticType"] == "UNVERIFIED", f"{key}: semantic type must remain unverified")
    _require(row["ReviewStatus"] == "REQUIRES_EXACT_SCHEMA_SEMANTIC_REVIEW",
             f"{key}: missing individual semantic-review gate")
    try:
      dom_count, mvl_count = int(row["DomOccurrences"]), int(row["MVLOccurrences"])
    except ValueError as error:
      raise CrosswalkError(f"{key}: non-integer occurrence count") from error
    _require(dom_count >= 0 and mvl_count >= 0, f"{key}: negative occurrence count")
    entries.append(QuarantineEntry(key, dom_count, mvl_count, row["DomExample"], row["MVLExample"],
                                   row["AcceptanceCriterion"]))
  return tuple(sorted(entries, key=lambda item: item.key))


def classify_key(key: str) -> tuple[str, str]:
  """Return a review priority, never a permission or semantic equivalence claim."""
  lowered = key.lower()
  high = [token for token in HIGH_RISK_TOKENS if token in lowered]
  life = [token for token in LIFECYCLE_TOKENS if token in lowered]
  if high:
    return "SENSITIVE_OR_HIGH_RISK", "lexical review signal: " + ",".join(high)
  if life:
    return "SENSITIVE_OR_HIGH_RISK", "lifecycle review signal: " + ",".join(life)
  return "LOW_RISK_CANDIDATE", "no configured high-risk lexical signal; still denied pending semantic review"


def _native_param_metadata(params_keys: Path, keys: set[str]) -> dict[str, dict[str, str]]:
  if not params_keys.is_file():
    return {}
  # This intentionally accepts only the simple literal entries in the MVL source map.
  pattern = re.compile(r'^\s*\{"([A-Za-z][A-Za-z0-9_]*)",\s*\{([^}]*)\}\},?\s*$')
  found: dict[str, dict[str, str]] = {}
  for line_number, line in enumerate(params_keys.read_text(encoding="utf-8").splitlines(), 1):
    match = pattern.match(line)
    if not match or match.group(1) not in keys:
      continue
    attributes = match.group(2).split(",")
    if len(attributes) >= 2:
      found[match.group(1)] = {"source": str(params_keys), "source_attested": False, "provenance": "UNVERIFIED_CALLER_SUPPLIED_FILE", "line": str(line_number),
                               "flags": attributes[0].strip(), "declared_type": attributes[1].strip()}
  return found


def build_crosswalk(quarantine: Path, params_keys: Path | None = None) -> dict:
  entries = load_quarantine(quarantine)
  native = _native_param_metadata(params_keys, {item.key for item in entries}) if params_keys else {}
  records = []
  for item in entries:
    classification, rationale = classify_key(item.key)
    records.append({
      "key": item.key, "classification": classification, "classification_rationale": rationale,
      "dom_literal_occurrences": item.dom_occurrences, "mvl_literal_occurrences": item.mvl_occurrences,
      "dom_example": item.dom_example, "mvl_example": item.mvl_example,
      "local_params_candidate_unattested": native.get(item.key),
      "decision": "DENY", "read_enabled": False, "write_enabled": False,
      "semantic_type": "UNVERIFIED", "review_status": "REQUIRES_EXACT_SCHEMA_SEMANTIC_REVIEW",
      "acceptance_criterion": item.acceptance_criterion,
    })
  digest = hashlib.sha256(quarantine.read_bytes()).hexdigest()
  return {"schema_version": 1, "tool": "starpilot_compat", "mode": "READ_ONLY_EVIDENCE_ONLY",
          "quarantine_sha256": digest, "entry_count": len(records), "approved_count": 0,
          "denied_count": len(records), "entries": records,
          "source_attested": False, "native_params_policy": "UNATTESTED_METADATA_ONLY; no Params reads/writes or key approvals"}


def crosswalk_csv(document: dict) -> str:
  fields = ("key", "classification", "classification_rationale", "decision", "read_enabled", "write_enabled",
            "semantic_type", "review_status", "dom_literal_occurrences", "mvl_literal_occurrences",
            "dom_example", "mvl_example", "local_params_candidate_unattested", "acceptance_criterion")
  import io
  stream = io.StringIO(newline="")
  writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
  writer.writeheader()
  for row in document["entries"]:
    rendered = dict(row)
    rendered["local_params_candidate_unattested"] = json.dumps(row["local_params_candidate_unattested"], sort_keys=True,
                                                            separators=(",", ":")) if row["local_params_candidate_unattested"] else ""
    writer.writerow({name: rendered[name] for name in fields})
  return stream.getvalue()


def inspect_literal_occurrences(mvl_root: Path, key: str, allowed_keys: Iterable[str]) -> list[dict[str, object]]:
  """Find literal text evidence only for a known quarantine key, without shelling out."""
  _require(KEY_RE.fullmatch(key) is not None and key in set(allowed_keys), "key is not a quarantined literal")
  root = mvl_root.resolve()
  _require(root.is_dir(), "MVL root is not a directory")
  results = []
  for path in sorted(root.rglob("*")):
    if not path.is_file() or ".git" in path.parts:
      continue
    resolved = path.resolve()
    if root not in resolved.parents and resolved != root:
      continue
    try:
      lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
      continue
    for number, line in enumerate(lines, 1):
      if key in line:
        results.append({"path": str(path.relative_to(root)), "line": number, "text": line.strip()[:500]})
  return results
