"""Offline, deny-by-default evidence tooling for the MVL/StarPilot boundary.

This package is deliberately not registered with any runtime service.
"""

from .crosswalk import CrosswalkError, build_crosswalk, inspect_literal_occurrences, load_quarantine

__all__ = ["CrosswalkError", "build_crosswalk", "inspect_literal_occurrences", "load_quarantine"]
