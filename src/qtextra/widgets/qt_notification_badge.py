"""Notification badge widget that can be attached to any Qt widget."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from qtpy.QtCore import QEvent, QSize, Qt
from qtpy.QtGui import QColor, QFont, QPainter, QPaintEvent
from qtpy.QtWidgets import QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_overlay import QtOverlay

BadgeState = ty.Literal["", "info", "success", "warning", "error"]
BadgeMode = ty.Literal["dot", "count"]
BadgeSize = ty.Literal["xs", "sm", "md", "lg", "xl"]


class QtNotificationBadge(QtOverlay):
    """Small badge that can be overlaid on any widget."""

    STATES: tuple[BadgeState, ...] = ("", "info", "success", "warning", "error")
    MODES: tuple[BadgeMode, ...] = ("dot", "count")
    SIZES: tuple[BadgeSize, ...] = ("xs", "sm", "md", "lg", "xl")
    SIZE_MAP: dict[BadgeSize, int] = {
        "xs": 10,
        "sm": 12,
        "md": 16,
        "lg": 20,
        "xl": 24,
    }
    STATE_COLOR_KEYS: dict[BadgeState, str] = {
        "info": "current",  # TODO: add better info color
        "success": "success",
        "warning": "warning",
        "error": "error",
    }
    MAX_COUNT = 99
    Y_OFFSET = 0

    def __init__(
        self,
        parent: QWidget | None = None,
        widget: QWidget | None = None,
        state: BadgeState = "error",
        mode: BadgeMode = "dot",
        size: BadgeSize = "md",
        count: int | None = None,
        visible_when_zero: bool = False,
        auto_clear_on_click: bool = False,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
    ):
        super().__init__(parent=parent, alignment=alignment)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self._state: BadgeState = "error"
        self._mode: BadgeMode = "dot"
        self._size: BadgeSize = "md"
        self._count = 0
        self._visible_when_zero = bool(visible_when_zero)
        self._auto_clear_on_click = bool(auto_clear_on_click)
        self._clear_target: QWidget | None = None

        with suppress(RuntimeError):
            THEMES.evt_theme_changed.connect(self._on_theme_changed)

        self.set_state(state)
        self.set_mode(mode)
        self.set_badge_size(size)
        self.set_count(count)
        if widget is not None:
            self.attach_to(widget)
        else:
            self._sync_visibility()

    @property
    def state(self) -> BadgeState:
        """Return current state."""
        return self._state

    def set_state(self, state: BadgeState) -> None:
        """Set visual badge state."""
        if state not in self.STATES:
            raise ValueError(f"Invalid state: {state}. Must be one of {self.STATES}")
        self._state = state
        self._sync_visibility()
        self.update()

    def clear(self) -> None:
        """Clear the badge state and hide it."""
        self.set_state("")

    @property
    def mode(self) -> BadgeMode:
        """Return current display mode."""
        return self._mode

    def set_mode(self, mode: BadgeMode) -> None:
        """Set badge display mode."""
        if mode not in self.MODES:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {self.MODES}")
        self._mode = mode
        self.updateGeometry()
        self._sync_visibility()
        self.update()

    @property
    def badge_size(self) -> BadgeSize:
        """Return current size preset."""
        return self._size

    def set_badge_size(self, size: BadgeSize) -> None:
        """Set badge size preset."""
        if size not in self.SIZES:
            raise ValueError(f"Invalid size: {size}. Must be one of {self.SIZES}")
        self._size = size
        diameter = self._diameter
        self.setMinimumSize(QSize(diameter, diameter))
        self.updateGeometry()
        self.update()

    @property
    def count(self) -> int:
        """Return badge count."""
        return self._count

    def set_count(self, count: int | None) -> None:
        """Set badge count."""
        if count is None:
            count = 0
        if count < 0:
            raise ValueError("Badge count must be >= 0")
        self._count = int(count)
        self.updateGeometry()
        self._sync_visibility()
        self.update()

    def set_visible_when_zero(self, visible: bool) -> None:
        """Control whether count mode shows when count is zero."""
        self._visible_when_zero = bool(visible)
        self._sync_visibility()

    def set_auto_clear_on_click(self, state: bool) -> None:
        """Clear the badge when the attached widget is clicked."""
        self._auto_clear_on_click = bool(state)
        self._update_clear_target()

    def attach_to(self, widget: QWidget | None) -> None:
        """Attach the badge overlay to a target widget."""
        if widget is not None and self.parentWidget() is None:
            self.setParent(widget.window())
        self.set_widget(widget)
        self._update_clear_target()
        self._sync_visibility()

    def eventFilter(self, recv, event):  # type: ignore[override]
        """Clear the badge when the target widget is clicked."""
        if (
            recv is self._clear_target
            and self._auto_clear_on_click
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.clear()
        return super().eventFilter(recv, event)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Return badge size."""
        diameter = self._diameter
        text = self._display_text
        if self._mode == "dot" or not text:
            return QSize(diameter, diameter)
        metrics = self.fontMetrics()
        width = max(diameter, metrics.horizontalAdvance(text) + max(6, diameter // 2))
        return QSize(width, diameter)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        """Return minimum badge size."""
        return self.sizeHint()

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        """Paint badge background and optional count."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = QColor(self._background_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(self.rect(), self.height() / 2, self.height() / 2)

        text = self._display_text
        if self._mode == "count" and text:
            painter.setPen(QColor(self._text_color))
            painter.setFont(self._badge_font())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

        painter.end()
        del event

    @property
    def _diameter(self) -> int:
        return self.SIZE_MAP[self._size]

    @property
    def _display_text(self) -> str:
        if self._mode != "count":
            return ""
        if self._count <= 0 and not self._visible_when_zero:
            return ""
        return f"{self.MAX_COUNT}+" if self._count > self.MAX_COUNT else str(self._count)

    @property
    def _background_color(self) -> str:
        return THEMES.get_hex_color(self.STATE_COLOR_KEYS[self._state])

    @property
    def _text_color(self) -> str:
        return THEMES.get_text_color_for_background(self._background_color)

    def _badge_font(self) -> QFont:
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSizeF(max(6.0, self._diameter * 0.48))
        return font

    def _sync_visibility(self) -> None:
        has_widget = self.widget() is not None
        should_show = (
            has_widget and bool(self._state) and (self._mode == "dot" or self._count > 0 or self._visible_when_zero)
        )
        self.setVisible(should_show)

    def _on_theme_changed(self) -> None:
        self.update()

    def _update_clear_target(self) -> None:
        widget = self.widget()
        if self._clear_target is widget:
            return
        if self._clear_target is not None:
            self._clear_target.removeEventFilter(self)
        self._clear_target = widget
        if self._clear_target is not None and self._auto_clear_on_click:
            self._clear_target.installEventFilter(self)
