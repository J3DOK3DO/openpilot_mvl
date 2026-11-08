"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import pyray as rl
import time
from collections.abc import Callable
from openpilot.selfdrive.ui.layouts.home import HomeLayout, HomeLayoutState, HEAD_BUTTON_FONT_SIZE, SPACING
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot
from openpilot.sunnypilot.starpilot_views.offroad import build_offroad_home_presentation
from openpilot.system.ui.lib.application import gui_app, FontWeight, TextAlignment
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.lib.multilang import tr, trn
from openpilot.system.ui.widgets.label import gui_label

BRAND_FONT_SIZE = 48
BRAND_DESC_SPACING = 12
MAX_STATUS_SNAPSHOT_AGE_NS = 2_000_000_000


class HomeLayoutSP(HomeLayout):
  def __init__(self):
    super().__init__()
    # No Params key or subscriber enables this optional read-only view.
    self._status_snapshot_supplier: Callable[[], BridgeSnapshot] | None = None

  def set_status_snapshot_supplier(self, supplier: Callable[[], BridgeSnapshot] | None) -> None:
    """Accept an explicitly owned read-only snapshot source; None disables it."""
    if supplier is not None and not callable(supplier):
      raise TypeError("supplier must be callable or None")
    self._status_snapshot_supplier = supplier

  def _render_header(self):
    font = gui_app.font(FontWeight.MEDIUM)

    version_text_width = self.header_rect.width

    if self.update_available:
      version_text_width -= self.update_notif_rect.width

      highlight_color = rl.Color(75, 95, 255, 255) if self.current_state == HomeLayoutState.UPDATE else rl.Color(54, 77, 239, 255)
      rl.draw_rectangle_rounded(self.update_notif_rect, 0.3, 10, highlight_color)

      text = tr("UPDATE")
      text_size = measure_text_cached(font, text, HEAD_BUTTON_FONT_SIZE)
      text_x = self.update_notif_rect.x + (self.update_notif_rect.width - text_size.x) // 2
      text_y = self.update_notif_rect.y + (self.update_notif_rect.height - text_size.y) // 2
      rl.draw_text_ex(font, text, rl.Vector2(int(text_x), int(text_y)), HEAD_BUTTON_FONT_SIZE, 0, rl.WHITE)

    if self.alert_count > 0:
      version_text_width -= self.alert_notif_rect.width

      highlight_color = rl.Color(255, 70, 70, 255) if self.current_state == HomeLayoutState.ALERTS else rl.Color(226, 44, 44, 255)
      rl.draw_rectangle_rounded(self.alert_notif_rect, 0.3, 10, highlight_color)

      alert_text = trn("{} ALERT", "{} ALERTS", self.alert_count).format(self.alert_count)
      text_size = measure_text_cached(font, alert_text, HEAD_BUTTON_FONT_SIZE)
      text_x = self.alert_notif_rect.x + (self.alert_notif_rect.width - text_size.x) // 2
      text_y = self.alert_notif_rect.y + (self.alert_notif_rect.height - text_size.y) // 2
      rl.draw_text_ex(font, alert_text, rl.Vector2(int(text_x), int(text_y)), HEAD_BUTTON_FONT_SIZE, 0, rl.WHITE)

    if self.update_available or self.alert_count > 0:
      version_text_width -= SPACING * 1.5

    version_right = self.header_rect.x + self.header_rect.width
    version_left = version_right - version_text_width

    brand = "sunnypilot"
    description = self.params.get("UpdaterCurrentDescription") or ""

    desc_width = 0
    if description:
      desc_size = measure_text_cached(gui_app.font(FontWeight.NORMAL), description, BRAND_FONT_SIZE)
      desc_width = desc_size.x
      desc_rect = rl.Rectangle(version_right - desc_width, self.header_rect.y, desc_width, self.header_rect.height)
      gui_label(desc_rect, description, BRAND_FONT_SIZE, rl.WHITE, alignment=TextAlignment.RIGHT)

    brand_size = measure_text_cached(gui_app.font(FontWeight.AUDIOWIDE), brand, BRAND_FONT_SIZE)
    spacing = BRAND_DESC_SPACING if description else 0
    brand_x = version_right - desc_width - spacing - brand_size.x
    brand_rect = rl.Rectangle(max(version_left, brand_x), self.header_rect.y, brand_size.x, self.header_rect.height)
    gui_label(brand_rect, brand, BRAND_FONT_SIZE, rl.WHITE, font_weight=FontWeight.AUDIOWIDE)
    self._render_status_badge(brand_x)

  def _render_status_badge(self, brand_x: float) -> None:
    """Draw one optional status line only in unused header space."""
    supplier = self._status_snapshot_supplier
    if (supplier is None or not self.is_visible or self.current_state != HomeLayoutState.HOME or
        self.update_available or self.alert_count > 0 or ui_state.started):
      return
    width = min(520.0, brand_x - self.header_rect.x - 24.0)
    if width < 300.0 or self.header_rect.height < 64.0:
      return
    try:
      snapshot = supplier()
      # The view model checks topic age against snapshot time. Also check the
      # snapshot against the UI clock so a cached result cannot stay visible.
      now_ns = time.monotonic_ns()
      if (type(snapshot) is not BridgeSnapshot or type(snapshot.now_ns) is not int or
          not 0 <= now_ns - snapshot.now_ns <= MAX_STATUS_SNAPSHOT_AGE_NS):
        return
      for status in (snapshot.device, snapshot.selfdrive, snapshot.car):
        if status is not None and (type(status.timestamp_ns) is not int or
                                   not 0 <= now_ns - status.timestamp_ns <= MAX_STATUS_SNAPSHOT_AGE_NS):
          return
      presentation = build_offroad_home_presentation(
        snapshot, width=width, height=self.header_rect.height,
        started=ui_state.started, home_visible=self.is_visible,
        update_present=self.update_available, alerts_present=self.alert_count > 0,
      )
    except Exception:
      return
    if presentation.defer_to_mvl or not presentation.panels:
      return
    # The native update/alert widgets and brand remain fully owned by MVL.
    panel = presentation.panels[0]
    badge = rl.Rectangle(self.header_rect.x, self.header_rect.y + 4, width, self.header_rect.height - 8)
    try:
      rl.draw_rectangle_rounded(badge, 0.15, 8, rl.Color(35, 47, 59, 255))
      gui_label(rl.Rectangle(badge.x + 16, badge.y, badge.width - 32, badge.height),
                f"{panel.title}: {panel.value}", 25, rl.WHITE)
    except Exception:
      # A failure in the optional badge must not interrupt MVL's header.
      return
