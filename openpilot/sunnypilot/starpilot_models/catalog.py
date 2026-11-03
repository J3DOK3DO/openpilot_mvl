"""Bounded, read-only parsing and verification for caller-supplied model inventory.

This module intentionally has no discovery, downloads, writes, subprocesses,
or model execution.  A caller must explicitly choose both a catalog entry and
a relative file beneath its injected trusted directory before verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
from typing import Final


MAX_CATALOG_BYTES: Final = 256 * 1024
MAX_ENTRIES: Final = 128
MAX_STRING_LENGTH: Final = 128
MAX_RUNTIME_COUNT: Final = 8
MAX_MODEL_BYTES: Final = 2 * 1024 * 1024 * 1024
STREAM_CHUNK_BYTES: Final = 64 * 1024
SUPPORTED_ARCHES: Final = frozenset(("x86_64", "aarch64"))
SUPPORTED_AGNOS: Final = "19.8.1"
ALLOWED_RUNTIMES: Final = frozenset(("onnxruntime", "qnn", "snpe", "tinygrad"))
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class CatalogError(ValueError):
  """The untrusted inventory or verification request violated the safe schema."""


class Verification(str, Enum):
  PASS = "PASS"
  HOLD = "HOLD"


class Compatibility(str, Enum):
  COMPATIBLE_METADATA_ONLY = "COMPATIBLE_METADATA_ONLY"
  HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class ModelEntry:
  """Immutable allowlisted metadata, not an executable model declaration."""

  model_id: str
  name: str
  version: str
  sha256: str
  size: int
  target_abi: str
  expected_runtimes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelCatalog:
  """Immutable inventory.  An empty catalog is valid and remains disabled."""

  entries: tuple[ModelEntry, ...]

  def get(self, model_id: str) -> ModelEntry | None:
    """Return only an explicitly named entry; no automatic model selection occurs."""
    for entry in self.entries:
      if entry.model_id == model_id:
        return entry
    return None


DEFAULT_CATALOG: Final = ModelCatalog(())


@dataclass(frozen=True, slots=True)
class VerificationResult:
  status: Verification
  reason: str
  bytes_hashed: int = 0


def _require_string(value: object, field: str) -> str:
  if not isinstance(value, str) or not value or len(value) > MAX_STRING_LENGTH:
    raise CatalogError(f"{field} must be a non-empty bounded string")
  return value


def _require_identifier(value: object, field: str) -> str:
  result = _require_string(value, field)
  if _IDENTIFIER.fullmatch(result) is None:
    raise CatalogError(f"{field} has unsafe characters")
  return result


def _parse_entry(value: object) -> ModelEntry:
  if not isinstance(value, dict):
    raise CatalogError("each model entry must be an object")
  expected = {"id", "name", "version", "sha256", "size", "target_abi", "expected_runtimes"}
  if set(value) != expected:
    raise CatalogError("model entry fields must exactly match the allowlisted schema")
  model_id = _require_identifier(value["id"], "id")
  name = _require_identifier(value["name"], "name")
  version = _require_identifier(value["version"], "version")
  digest = _require_string(value["sha256"], "sha256")
  if _DIGEST.fullmatch(digest) is None:
    raise CatalogError("sha256 must be 64 lowercase hexadecimal characters")
  size = value["size"]
  if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_MODEL_BYTES:
    raise CatalogError("size must be a bounded non-negative integer")
  target_abi = value["target_abi"]
  if not isinstance(target_abi, str) or target_abi not in SUPPORTED_ARCHES:
    raise CatalogError("target_abi is not allowlisted")
  runtimes = value["expected_runtimes"]
  if not isinstance(runtimes, list) or len(runtimes) > MAX_RUNTIME_COUNT:
    raise CatalogError("expected_runtimes must be a bounded list")
  if any(not isinstance(runtime, str) or runtime not in ALLOWED_RUNTIMES for runtime in runtimes):
    raise CatalogError("expected_runtimes contains a non-allowlisted runtime")
  if len(set(runtimes)) != len(runtimes):
    raise CatalogError("expected_runtimes must not contain duplicates")
  return ModelEntry(model_id, name, version, digest, size, target_abi, tuple(runtimes))


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
  result: dict[str, object] = {}
  for key, value in pairs:
    if key in result:
      raise CatalogError("JSON object contains a duplicate field")
    result[key] = value
  return result


def parse_catalog(raw: str | bytes | bytearray) -> ModelCatalog:
  """Parse only the bounded JSON inventory supplied directly by the caller."""
  if not isinstance(raw, (str, bytes, bytearray)):
    raise CatalogError("catalog must be JSON text or bytes")
  raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
  if len(raw_bytes) > MAX_CATALOG_BYTES:
    raise CatalogError("catalog exceeds byte limit")
  try:
    decoded = json.loads(raw_bytes, object_pairs_hook=_reject_duplicate_keys)
  except CatalogError:
    raise
  except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
    raise CatalogError("catalog is not valid JSON") from error
  if not isinstance(decoded, dict) or set(decoded) != {"models"}:
    raise CatalogError("catalog must be an object with only models")
  models = decoded["models"]
  if not isinstance(models, list) or len(models) > MAX_ENTRIES:
    raise CatalogError("models must be a bounded list")
  entries = tuple(_parse_entry(item) for item in models)
  ids = tuple(entry.model_id for entry in entries)
  if len(set(ids)) != len(ids):
    raise CatalogError("duplicate model id")
  return ModelCatalog(entries)


def _hold(reason: str, bytes_hashed: int = 0) -> VerificationResult:
  return VerificationResult(Verification.HOLD, reason, bytes_hashed)


def verify_selected_file(entry: ModelEntry, allowed_directory: Path, relative_path: str) -> VerificationResult:
  """Hash only an explicitly selected regular file using no-follow directory FDs.

  Holding each opened directory FD while descending prevents a symlink swap
  between validating a path and opening the selected model. No uploads, writes,
  downloads or model activation occur here.
  """
  if not isinstance(allowed_directory, Path):
    return _hold("allowed directory must be a Path")
  if not isinstance(relative_path, str) or not relative_path or "\\0" in relative_path:
    return _hold("selected path must be a non-empty relative string")
  selected = Path(relative_path)
  if selected.is_absolute() or any(part in ("", ".", "..") for part in selected.parts):
    return _hold("selected path is unsafe")
  dir_fd = None
  file_fd = None
  bytes_hashed = 0
  directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
  file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
  try:
    dir_fd = os.open(allowed_directory, directory_flags)
    for part in selected.parts[:-1]:
      next_fd = os.open(part, directory_flags, dir_fd=dir_fd)
      os.close(dir_fd)
      dir_fd = next_fd
    file_fd = os.open(selected.parts[-1], file_flags, dir_fd=dir_fd)
    info = os.fstat(file_fd)
    if not stat.S_ISREG(info.st_mode):
      return _hold("selected path is not a regular file")
    if info.st_size != entry.size:
      return _hold("size mismatch")
    digest = hashlib.sha256()
    with os.fdopen(os.dup(file_fd), "rb") as model_file:
      while chunk := model_file.read(STREAM_CHUNK_BYTES):
        bytes_hashed += len(chunk)
        if bytes_hashed > entry.size:
          return _hold("file changed while hashing", bytes_hashed)
        digest.update(chunk)
    if bytes_hashed != entry.size:
      return _hold("file changed while hashing", bytes_hashed)
    if not hmac.compare_digest(digest.hexdigest(), entry.sha256):
      return _hold("sha256 mismatch", bytes_hashed)
    return VerificationResult(Verification.PASS, "digest and size match", bytes_hashed)
  except OSError as exc:
    if exc.errno in (errno.ELOOP, errno.ENOTDIR):
      return _hold("symlinks are denied", bytes_hashed)
    return _hold("selected file could not be safely opened", bytes_hashed)
  finally:
    if file_fd is not None:
      os.close(file_fd)
    if dir_fd is not None:
      os.close(dir_fd)


def check_compatibility(entry: ModelEntry, target_arch: str | None, agnos_version: str | None) -> Compatibility:
  """Evaluate declared metadata only; it never attests a loadable runtime or ABI."""
  if target_arch not in SUPPORTED_ARCHES or agnos_version != SUPPORTED_AGNOS:
    return Compatibility.HOLD
  if entry.target_abi != target_arch:
    return Compatibility.HOLD
  return Compatibility.COMPATIBLE_METADATA_ONLY
