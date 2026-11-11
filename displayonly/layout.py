#!/usr/bin/env python3
"""Pure layout model for the R3 disconnected MVL-StarPilot display.

This module deliberately imports no pyray, openpilot, cereal, msgq, Params, or
hardware interfaces.  It makes both production layouts testable without a GPU.
"""
from __future__ import annotations

from dataclasses import dataclass


COMPACT_SIZE = (536, 240)
LARGE_SIZE = (2160, 1080)


@dataclass(frozen=True)
class Command:
  kind: str
  bounds: tuple[int, int, int, int]
  color: str
  text: str = ""
  size: int = 0
  align: str = "left"


PALETTE = {
  "background": (7, 11, 17, 255),
  "panel": (19, 27, 37, 255),
  "panel_alt": (25, 35, 47, 255),
  "line": (55, 71, 88, 255),
  "white": (245, 247, 250, 255),
  "muted": (157, 171, 187, 255),
  "green": (42, 205, 125, 255),
  "amber": (255, 181, 46, 255),
  "red": (238, 91, 91, 255),
  "blue": (72, 156, 255, 255),
}


def _rect(x: int, y: int, w: int, h: int, color: str) -> Command:
  return Command("rect", (x, y, w, h), color)


def _line(x: int, y: int, w: int, h: int, color: str) -> Command:
  return Command("line", (x, y, w, h), color)


def _circle(x: int, y: int, radius: int, color: str) -> Command:
  return Command("circle", (x - radius, y - radius, radius * 2, radius * 2), color)


def _text(text: str, x: int, y: int, w: int, h: int, size: int,
          color: str, align: str = "left") -> Command:
  return Command("text", (x, y, w, h), color, text, size, align)


def compact_commands(demo: bool = False) -> list[Command]:
  c = [_rect(0, 0, 536, 240, "background"), _rect(0, 0, 536, 43, "panel"),
       _circle(22, 21, 7, "green"),
       _text("MVL STARPILOT", 38, 8, 190, 28, 19, "white"),
       _text("DISPLAY ONLY", 372, 10, 146, 24, 16, "green", "right")]
  if demo:
    c += [_rect(0, 43, 536, 28, "amber"),
          _text("DEMO / OFFLINE - RECORDED FIXTURE", 8, 47, 520, 20, 15, "background", "center"),
          _line(186, 196, 164, 0, "blue"), _circle(268, 184, 7, "blue"),
          _text("STATIC ROUTE PREVIEW", 156, 83, 224, 22, 17, "muted", "center"),
          _text("NO LIVE VEHICLE VALUES", 108, 112, 320, 30, 21, "white", "center")]
  else:
    c += [_text("--", 208, 48, 120, 70, 66, "white", "center"),
          _text("NO VEHICLE DATA", 118, 119, 300, 28, 23, "amber", "center")]
  c += [_rect(16, 158, 504, 42, "panel_alt"),
        _circle(35, 179, 5, "red"),
        _text("DISCONNECTED", 48, 168, 142, 22, 16, "white"),
        _text("ACTUATION DISABLED", 291, 168, 211, 22, 16, "red", "right"),
        _text("NO PANDA  |  NO CAN  |  NO CONTROLS  |  NO PUBLISHERS", 18, 211, 500, 17, 12, "muted", "center")]
  return c


def large_commands(demo: bool = False) -> list[Command]:
  c = [_rect(0, 0, 2160, 1080, "background"), _rect(0, 0, 2160, 116, "panel"),
       _circle(64, 58, 18, "green"),
       _text("MVL STARPILOT", 104, 25, 700, 66, 52, "white"),
       _text("DISPLAY ONLY", 1530, 31, 560, 58, 40, "green", "right"),
       _rect(80, 156, 2000, 690, "panel"),
       _rect(112, 188, 470, 626, "panel_alt"),
       _text("CONNECTION", 148, 226, 398, 42, 28, "muted"),
       _circle(161, 320, 11, "red"),
       _text("DISCONNECTED", 194, 291, 340, 58, 38, "white"),
       _line(148, 380, 398, 0, "line"),
       _text("DATA SOURCE", 148, 420, 398, 36, 24, "muted"),
       _text("NONE", 148, 466, 398, 52, 36, "amber"),
       _text("CONTROL PATH", 148, 565, 398, 36, 24, "muted"),
       _text("NOT PRESENT", 148, 611, 398, 52, 36, "green"),
       _text("HARDWARE STATUS", 148, 710, 398, 32, 24, "muted"),
       _text("PHYSICAL TEST PENDING", 148, 751, 398, 32, 22, "white")]
  if demo:
    c += [_rect(614, 188, 1434, 72, "amber"),
          _text("DEMO / OFFLINE - RECORDED STATIC FIXTURE", 640, 204, 1382, 42, 28, "background", "center"),
          _line(1050, 650, 560, -245, "blue"), _line(1050, 650, 560, 0, "line"),
          _circle(1330, 528, 18, "blue"),
          _text("STATIC ROUTE PREVIEW", 785, 318, 1090, 62, 42, "muted", "center"),
          _text("NO SPEED / STEERING / ACC / CAR STATE", 730, 704, 1200, 52, 34, "white", "center")]
  else:
    c += [_text("--", 884, 264, 900, 300, 250, "white", "center"),
          _text("NO VEHICLE DATA", 740, 584, 1190, 88, 68, "amber", "center"),
          _text("Safe disconnected state", 790, 690, 1090, 52, 34, "muted", "center")]
  c += [_rect(80, 878, 2000, 122, "panel_alt"),
        _text("ACTUATION DISABLED", 126, 900, 700, 62, 46, "red"),
        _text("No manager  |  No Panda/CAN  |  No vehicle publishers  |  No network", 780, 909, 1254, 50, 30, "muted", "right"),
        _text("STANDALONE READ-ONLY DASHBOARD", 80, 1023, 2000, 30, 22, "muted", "center")]
  return c


def commands(layout: str, demo: bool = False) -> tuple[tuple[int, int], list[Command]]:
  if layout == "compact":
    return COMPACT_SIZE, compact_commands(demo)
  if layout == "large":
    return LARGE_SIZE, large_commands(demo)
  raise ValueError("layout must be compact or large")


def validate(layout: str, demo: bool = False) -> list[str]:
  (width, height), items = commands(layout, demo)
  errors = []
  for index, item in enumerate(items):
    x, y, w, h = item.bounds
    if item.kind == "line":
      outside = min(x, x + w, y, y + h) < 0 or max(x, x + w) > width or max(y, y + h) > height
    else:
      outside = min(x, y, w, h) < 0 or x + w > width or y + h > height
    if outside:
      errors.append(f"command {index} outside {width}x{height}: {item}")
    if item.kind == "text":
      # Conservative ASCII width estimate; renderer additionally measures exactly.
      estimated = len(item.text) * item.size * 0.61
      if estimated > w:
        errors.append(f"text {index} may clip: {item.text!r} ({estimated:.1f}>{w})")
  return errors
