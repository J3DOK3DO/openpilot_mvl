"""Offline, default-disabled model catalog metadata and integrity helpers.

Importing this package performs no file access, process launch, network access,
model activation, or registration.  It is deliberately not wired into modeld.
"""

from .catalog import (
  CatalogError,
  Compatibility,
  DEFAULT_CATALOG,
  ModelCatalog,
  ModelEntry,
  Verification,
  check_compatibility,
  parse_catalog,
  verify_selected_file,
)

__all__ = (
  "CatalogError",
  "Compatibility",
  "DEFAULT_CATALOG",
  "ModelCatalog",
  "ModelEntry",
  "Verification",
  "check_compatibility",
  "parse_catalog",
  "verify_selected_file",
)
