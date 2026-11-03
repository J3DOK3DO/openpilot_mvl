"""Strict, in-memory feature selection for the read-only bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class Feature(str, Enum):
  DEVICE_STATUS = "device_status"
  SELFDRIVE_STATUS = "selfdrive_status"
  CAR_STATUS = "car_status"


class FeatureConfigurationError(ValueError):
  """A feature selection is unknown or not an exact bool."""


@dataclass(frozen=True)
class FeatureRegistry:
  """Immutable registry whose three features are disabled unless opted in.

  This object intentionally has no Params integration, persistence, environment
  lookup, or implicit default migration.
  """

  values: Mapping[Feature, bool] = field(default_factory=dict)

  def __post_init__(self) -> None:
    normalized: dict[Feature, bool] = {feature: False for feature in Feature}
    for key, value in self.values.items():
      feature = _coerce_feature(key)
      if type(value) is not bool:
        raise FeatureConfigurationError(f"{feature.value} must be bool, not {type(value).__name__}")
      normalized[feature] = value
    object.__setattr__(self, "values", MappingProxyType(normalized))

  @classmethod
  def from_overrides(cls, overrides: Mapping[str | Feature, bool]) -> "FeatureRegistry":
    if not isinstance(overrides, Mapping):
      raise FeatureConfigurationError("feature overrides must be a mapping")
    return cls(overrides)

  def enabled(self, feature: str | Feature) -> bool:
    return self.values[_coerce_feature(feature)]

  def active_topics(self) -> tuple[str, ...]:
    topics: list[str] = []
    if self.enabled(Feature.DEVICE_STATUS):
      topics.append("deviceState")
    if self.enabled(Feature.SELFDRIVE_STATUS):
      topics.append("selfdriveState")
    if self.enabled(Feature.CAR_STATUS):
      topics.append("carState")
    return tuple(topics)


def _coerce_feature(value: str | Feature) -> Feature:
  if isinstance(value, Feature):
    return value
  if type(value) is not str:
    raise FeatureConfigurationError("feature name must be a string")
  try:
    return Feature(value)
  except ValueError as exc:
    raise FeatureConfigurationError(f"unknown feature: {value!r}") from exc
