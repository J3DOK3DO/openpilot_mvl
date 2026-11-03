import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from openpilot.sunnypilot.starpilot_compat.crosswalk import CrosswalkError, build_crosswalk, crosswalk_csv, inspect_literal_occurrences, load_quarantine
from openpilot.sunnypilot.starpilot_compat.inventory import build_message_inventory


ROOT = Path(__file__).resolve().parents[4]
QUARANTINE = ROOT / "docs/engineering/mvl_starpilot_m0m3/SHARED_PARAMS_QUARANTINE_254.csv"
PARAMS = ROOT / "openpilot/common/params_keys.h"


def test_254_entries_are_unique_and_denied():
  entries = load_quarantine(QUARANTINE)
  document = build_crosswalk(QUARANTINE, PARAMS)
  assert len(entries) == document["entry_count"] == document["denied_count"] == 254
  assert document["approved_count"] == 0
  assert all(row["decision"] == "DENY" and not row["read_enabled"] and not row["write_enabled"] for row in document["entries"])


def test_schema_and_native_metadata_do_not_authorize_migration():
  document = build_crosswalk(QUARANTINE, PARAMS)
  token = next(row for row in document["entries"] if row["key"] == "AccessToken")
  assert token["local_params_candidate_unattested"]["declared_type"] == "STRING"
  assert token["decision"] == "DENY"
  assert document["native_params_policy"].startswith("UNATTESTED_METADATA_ONLY")


def test_deterministic_json_and_csv():
  first = build_crosswalk(QUARANTINE, PARAMS)
  second = build_crosswalk(QUARANTINE, PARAMS)
  assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
  rendered = crosswalk_csv(first)
  assert rendered == crosswalk_csv(second)
  assert len(list(csv.DictReader(rendered.splitlines()))) == 254


def test_collisions_missing_fields_and_bad_deny_contract_are_rejected(tmp_path):
  rows = list(csv.DictReader(QUARANTINE.open()))
  rows[1]["Key"] = rows[0]["Key"]
  broken = tmp_path / "duplicate.csv"
  with broken.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows)
  with pytest.raises(CrosswalkError, match="duplicate"):
    load_quarantine(broken)
  rows = list(csv.DictReader(QUARANTINE.open()))
  rows[0]["ReadEnabled"] = "TRUE"
  with broken.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows)
  with pytest.raises(CrosswalkError, match="reads and writes"):
    load_quarantine(broken)
  broken.write_text("Key\nAccessToken\n", encoding="utf-8")
  with pytest.raises(CrosswalkError, match="columns"):
    load_quarantine(broken)


def test_untrusted_key_is_rejected_and_literal_inspection_is_scoped(tmp_path):
  with pytest.raises(CrosswalkError):
    inspect_literal_occurrences(tmp_path, "../../AccessToken", {"AccessToken"})
  sample = tmp_path / "source.py"
  sample.write_text('value = "AccessToken"\n', encoding="utf-8")
  found = inspect_literal_occurrences(tmp_path, "AccessToken", {"AccessToken"})
  assert found == [{"path": "source.py", "line": 1, "text": 'value = "AccessToken"'}]


def test_source_backed_inventory_refuses_missing_car_schema():
  inventory = build_message_inventory(ROOT)
  messages = {item["topic"]: item for item in inventory["messages"]}
  assert messages["deviceState"]["status"] == "LOCAL_SOURCE_UNATTESTED"
  assert any(field["name"] == "started" and field["capnp_type"] == "Bool" for field in messages["deviceState"]["fields"])
  assert messages["selfdriveState"]["status"] == "LOCAL_SOURCE_UNATTESTED"
  assert messages["carState"]["status"] == "SOURCE_UNAVAILABLE_REJECTED"


def test_cli_output_is_reproducible(tmp_path):
  command = [sys.executable, "-m", "openpilot.sunnypilot.starpilot_compat", "--quarantine", str(QUARANTINE),
             "--params-keys", str(PARAMS), "render", "--format", "json"]
  first = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True).stdout
  second = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True).stdout
  assert first == second and json.loads(first)["entry_count"] == 254
