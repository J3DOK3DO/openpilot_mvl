from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from openpilot.sunnypilot.starpilot_models.catalog import (
  CatalogError,
  Compatibility,
  DEFAULT_CATALOG,
  Verification,
  check_compatibility,
  parse_catalog,
  verify_selected_file,
)


def inventory(models: list[dict[str, object]]) -> str:
  return json.dumps({"models": models})


def metadata(data: bytes = b"safe offline model", **overrides: object) -> dict[str, object]:
  result: dict[str, object] = {
    "id": "accord-model",
    "name": "accord-model",
    "version": "1.0.0",
    "sha256": hashlib.sha256(data).hexdigest(),
    "size": len(data),
    "target_abi": "aarch64",
    "expected_runtimes": ["onnxruntime"],
  }
  result.update(overrides)
  return result


def test_empty_catalog_is_valid_and_default_disabled() -> None:
  assert DEFAULT_CATALOG.entries == ()
  catalog = parse_catalog('{"models": []}')
  assert catalog.entries == ()
  assert catalog.get("anything") is None


def test_valid_explicit_file_passes_and_metadata_compatibility_is_not_qualification(tmp_path: Path) -> None:
  data = b"safe offline model"
  selected = tmp_path / "nested" / "model.bin"
  selected.parent.mkdir()
  selected.write_bytes(data)
  entry = parse_catalog(inventory([metadata(data)])).get("accord-model")
  assert entry is not None
  assert verify_selected_file(entry, tmp_path, "nested/model.bin").status is Verification.PASS
  assert check_compatibility(entry, "aarch64", "19.8.1") is Compatibility.COMPATIBLE_METADATA_ONLY


@pytest.mark.parametrize("path", ["../model.bin", "/tmp/model.bin", "nested/../model.bin", "./model.bin", "model" + chr(0) + ".bin"])
def test_malicious_paths_are_held(tmp_path: Path, path: str) -> None:
  entry = parse_catalog(inventory([metadata()])).entries[0]
  assert verify_selected_file(entry, tmp_path, path).status is Verification.HOLD


def test_symlink_is_denied(tmp_path: Path) -> None:
  data = b"safe offline model"
  actual = tmp_path / "actual.bin"
  actual.write_bytes(data)
  link = tmp_path / "linked.bin"
  link.symlink_to(actual)
  entry = parse_catalog(inventory([metadata(data)])).entries[0]
  result = verify_selected_file(entry, tmp_path, "linked.bin")
  assert result.status is Verification.HOLD
  assert result.reason == "symlinks are denied"


def test_invalid_digest_and_duplicate_ids_are_rejected() -> None:
  with pytest.raises(CatalogError, match="sha256"):
    parse_catalog(inventory([metadata(sha256="not-a-digest")]))
  duplicate = [metadata(id="same"), metadata(id="same", name="different")]
  with pytest.raises(CatalogError, match="duplicate"):
    parse_catalog(inventory(duplicate))


def test_malicious_schema_values_are_rejected() -> None:
  with pytest.raises(CatalogError, match="target_abi"):
    parse_catalog(inventory([metadata(target_abi=["aarch64"])]))
  with pytest.raises(CatalogError, match="duplicate field"):
    parse_catalog('{"models": [], "models": []}')


def test_size_mismatch_and_digest_mismatch_hold(tmp_path: Path) -> None:
  selected = tmp_path / "model.bin"
  selected.write_bytes(b"actual")
  size_entry = parse_catalog(inventory([metadata(b"expected")])).entries[0]
  assert verify_selected_file(size_entry, tmp_path, "model.bin").reason == "size mismatch"
  digest_entry = parse_catalog(inventory([metadata(b"actual", sha256="0" * 64)])).entries[0]
  assert verify_selected_file(digest_entry, tmp_path, "model.bin").reason == "sha256 mismatch"


def test_unknown_or_mismatched_platform_holds() -> None:
  entry = parse_catalog(inventory([metadata()])).entries[0]
  assert check_compatibility(entry, None, "19.8.1") is Compatibility.HOLD
  assert check_compatibility(entry, "x86_64", "19.8.1") is Compatibility.HOLD
  assert check_compatibility(entry, "aarch64", "unknown") is Compatibility.HOLD


def test_parse_and_verification_do_not_write_modeld(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  modeld = tmp_path / "modeld"
  modeld.mkdir()
  sentinel = modeld / "untouched"
  sentinel.write_bytes(b"unchanged")
  allowed = tmp_path / "allowed"
  allowed.mkdir()
  (allowed / "model.bin").write_bytes(b"safe offline model")
  before = sentinel.read_bytes()
  monkeypatch.chdir(tmp_path)
  entry = parse_catalog(inventory([metadata()])).entries[0]
  assert verify_selected_file(entry, allowed, "model.bin").status is Verification.PASS
  assert sentinel.read_bytes() == before


def test_intermediate_symlink_is_rejected_by_descriptor_walk(tmp_path: Path):
  original = tmp_path / "original"
  original.mkdir()
  payload = b"safe offline model"
  (original / "model.bin").write_bytes(payload)
  (tmp_path / "alias").symlink_to(original, target_is_directory=True)
  entry = parse_catalog(inventory([metadata(payload)])).entries[0]
  result = verify_selected_file(entry, tmp_path, "alias/model.bin")
  assert result.status is Verification.HOLD
  assert result.reason == "symlinks are denied"


def test_allowed_root_symlink_is_rejected(tmp_path: Path):
  original = tmp_path / "original"
  original.mkdir()
  payload = b"safe offline model"
  (original / "model.bin").write_bytes(payload)
  root = tmp_path / "symlink_root"
  root.symlink_to(original, target_is_directory=True)
  entry = parse_catalog(inventory([metadata(payload)])).entries[0]
  result = verify_selected_file(entry, root, "model.bin")
  assert result.status is Verification.HOLD
  assert result.reason == "symlinks are denied"
