"""Explicitly invoked, read-only MVL status subscriber factory.

No subscribers are started when this package is imported. Feature configuration
comes from an immutable in-memory allowlist, not the vehicle's Params database.
"""

from __future__ import annotations

from typing import Any

from .features import FeatureRegistry


def create_mvl_submaster(registry: FeatureRegistry) -> Any:
  """Create a native *subscriber* only for enabled read-only status topics.

  The all-OFF path rejects before importing MVL's message library or creating
  any messaging sockets. Caller owns update and process lifetime.
  """
  if type(registry) is not FeatureRegistry:
    raise TypeError("registry must be FeatureRegistry")
  topics = registry.active_topics()
  if not topics:
    raise ValueError("all bridge features are disabled")
  from openpilot.cereal import messaging
  return messaging.SubMaster(list(topics))
