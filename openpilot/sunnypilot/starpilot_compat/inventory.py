"""Unattested local Cap'n Proto and IPC inventory; absence is recorded, not guessed."""
from __future__ import annotations

import re
from pathlib import Path

TARGETS = {"deviceState": ("DeviceState", "openpilot/cereal/log.capnp"),
           "selfdriveState": ("SelfdriveState", "openpilot/cereal/log.capnp"),
           "carState": ("CarState", "opendbc_repo/opendbc/car/car.capnp")}


def _direct_fields(source: Path, struct_name: str) -> list[dict[str, object]]:
  start = re.compile(rf"^struct\s+{re.escape(struct_name)}(?:\s|@)")
  field = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)\s+@(\d+)\s*:\s*([^;]+);")
  depth = 0
  active = False
  fields = []
  for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
    if not active:
      if start.match(line):
        active, depth = True, line.count("{") - line.count("}")
      continue
    if depth == 1:
      match = field.match(line)
      if match:
        fields.append({"name": match.group(1), "ordinal": int(match.group(2)), "capnp_type": match.group(3).strip(),
                       "source": str(source), "line": number})
    depth += line.count("{") - line.count("}")
    if depth == 0:
      return fields
  return []


def build_message_inventory(repository_root: Path) -> dict:
  """Build only facts represented in local source files."""
  messages = []
  services = repository_root / "openpilot/cereal/services.py"
  service_text = services.read_text(encoding="utf-8") if services.is_file() else ""
  for topic, (struct_name, relative_schema) in TARGETS.items():
    schema = repository_root / relative_schema
    if not schema.is_file():
      messages.append({"topic": topic, "status": "SOURCE_UNAVAILABLE_REJECTED", "fields": [],
                       "reason": f"required schema is absent: {relative_schema}"})
      continue
    messages.append({"topic": topic, "status": "LOCAL_SOURCE_UNATTESTED", "struct": struct_name,
                     "schema": relative_schema, "fields": _direct_fields(schema, struct_name),
                     "ipc_service_registered": f'"{topic}":' in service_text,
                     "ipc_source": "openpilot/cereal/services.py" if service_text else None,
                     "abi_mapping": "Cap'n Proto field ordinals/types from schema; Python IPC binding ABI is not inferred"})
  return {"schema_version": 1, "source_attested": False, "mode": "READ_ONLY_LOCAL_SOURCE_UNATTESTED_INVENTORY", "messages": messages,
          "abi_policy": "No Cython/nanobind compatibility claim; no mapping without local source evidence."}
