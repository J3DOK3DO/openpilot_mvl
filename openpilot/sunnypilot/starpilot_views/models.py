"""Immutable, renderer-neutral values; these types have no native UI dependency."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AlertPriority(Enum):
  INFO = 1
  LOW = 2
  HIGH = 3
  CRITICAL = 4


class LayoutKind(Enum):
  COMPACT = "compact"
  FULL = "full"


class Theme(Enum):
  DARK = "dark"
  LIGHT = "light"


@dataclass(frozen=True)
class Palette:
  background: str
  foreground: str
  accent: str
  caution: str


PALETTES = {
  Theme.DARK: Palette("#10151c", "#f2f5f7", "#58c4ff", "#ffc857"),
  Theme.LIGHT: Palette("#f4f7fa", "#17212b", "#0077b6", "#a85d00"),
}


@dataclass(frozen=True)
class Rect:
  x: float
  y: float
  width: float
  height: float


@dataclass(frozen=True)
class Alert:
  """Alert supplied by MVL/OEM policy; presentation never downgrades it."""

  source: str
  priority: AlertPriority
  message: str


@dataclass(frozen=True)
class StatusPanel:
  key: str
  title: str
  value: str
  bounds: Rect


@dataclass(frozen=True)
class Presentation:
  """M3 output. ``defer_to_mvl`` means no StarPilot content is renderable."""

  layout: LayoutKind
  palette: Palette
  panels: tuple[StatusPanel, ...]
  overlay: Alert | None
  protected_alerts: tuple[Alert, ...]
  defer_to_mvl: bool
  rejection_reasons: tuple[str, ...]
