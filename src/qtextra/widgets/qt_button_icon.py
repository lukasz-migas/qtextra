"""Custom image button class."""

from __future__ import annotations

import typing as ty
import warnings
from contextlib import suppress
from copy import deepcopy
from functools import partial

import qtawesome
from qtpy.QtCore import (  # type: ignore[attr-defined]
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from qtpy.QtGui import QBrush, QColor, QEnterEvent, QIcon, QPainter, QPolygonF, QResizeEvent
from qtpy.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.assets import get_icon
from qtextra.config import THEMES
from qtextra.typing import QtaSizePreset
from qtextra.widgets._qta_mixin import QtaMixin
from qtextra.widgets.qt_notification_badge import BadgeMode, BadgeSize, BadgeState, QtNotificationBadge
from qtextra.widgets.qt_tooltip_rich import QtRichToolTip

INDICATOR_TYPES = {"success": "success", "warning": "warning", "active": "progress"}

# Map button size presets to badge size presets so the count scales with the button.
PRESET_TO_BADGE_SIZE: dict[str, BadgeSize] = {
    "xxsmall": "xs",
    "xsmall": "xs",
    "small": "sm",
    "normal": "md",
    "average": "md",
    "medium": "lg",
    "large": "lg",
    "xlarge": "xl",
    "xxlarge": "xl",
    "xxxlarge": "xl",
}


class QtImagePushButton(QPushButton, QtaMixin):
    """Image button."""

    evt_click = Signal(QPushButton)
    evt_right_click = Signal(QPushButton)
    count: int = 0
    count_enabled: bool = False
    has_right_click: bool = False
    menu_enabled: bool = False

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        self._icon_color = kwargs.pop("icon_color_override", None)
        self._badge: QtNotificationBadge | None = None
        self._base_button_size: QSize = QSize(20, 20)
        super().__init__()
        self.setFixedSize(20, 20)
        self.setProperty("transparent", False)
        self.transparent = False
        with suppress(RuntimeError):
            THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def set_count(self, count: int, enabled: bool = True) -> None:
        """Enable a count indicator."""
        self.count = count
        self.count_enabled = enabled
        badge = self._ensure_badge()
        badge.set_mode("count")
        badge.set_state("info" if enabled else "")
        badge.set_count(count if enabled else 0)
        self._refresh_button_footprint()

    def set_badge(
        self,
        *,
        count: int | None = None,
        state: BadgeState = "info",
        mode: BadgeMode = "count",
        visible_when_zero: bool = False,
    ) -> None:
        """Configure the badge overlay with full control over state and mode."""
        badge = self._ensure_badge()
        badge.set_state(state)
        badge.set_mode(mode)
        badge.set_visible_when_zero(visible_when_zero)
        if mode == "count":
            badge.set_count(count if count is not None else self.count)
            if count is not None:
                self.count = count
            self.count_enabled = bool(state)
        self._refresh_button_footprint()

    def clear_badge(self) -> None:
        """Clear any badge currently displayed on this button."""
        self.count = 0
        self.count_enabled = False
        if self._badge is not None:
            self._badge.clear()
        self._refresh_button_footprint()

    def _ensure_badge(self) -> QtNotificationBadge:
        """Lazily construct and attach the badge overlay."""
        if self._badge is None:
            badge = QtNotificationBadge(state="info", mode="count", size=self._preset_to_badge_size())
            badge.attach_to(self)
            self._badge = badge
        else:
            self._badge.set_badge_size(self._preset_to_badge_size())
        return self._badge

    def _preset_to_badge_size(self) -> BadgeSize:
        """Pick a badge size that matches the current button size preset."""
        preset = self.property("qta_size_preset")
        if isinstance(preset, str) and preset in PRESET_TO_BADGE_SIZE:
            return PRESET_TO_BADGE_SIZE[preset]
        height = self._base_button_size.height() or self.height() or self.sizeHint().height()
        if height < 16:
            return "xs"
        if height < 24:
            return "sm"
        if height < 40:
            return "md"
        if height < 80:
            return "lg"
        return "xl"

    def _refresh_button_footprint(self) -> None:
        """Refresh the badge overlay without changing the button footprint."""
        self.setContentsMargins(0, 0, 0, 0)
        if self._badge is not None:
            self._badge.set_badge_size(self._preset_to_badge_size())
            self._badge._relayout()
            self._badge._sync_visibility()
        self.updateGeometry()

    def setFixedSize(self, *args: ty.Any, **kwargs: ty.Any) -> None:  # type: ignore[override]
        """Capture and apply the fixed button footprint."""
        if len(args) == 1 and isinstance(args[0], QSize):
            self._base_button_size = QSize(args[0])
        elif len(args) == 2:
            self._base_button_size = QSize(int(args[0]), int(args[1]))
        else:
            super().setFixedSize(*args, **kwargs)
            self._base_button_size = QSize(self.minimumSize())
            self._refresh_button_footprint()
            return
        super().setFixedSize(self._base_button_size)
        self._refresh_button_footprint()

    def _apply_qta_size(  # type: ignore[override]
        self,
        widget_size: QSize,
        icon_size: QSize,
        *,
        preset: QtaSizePreset | None = None,
        use_legacy_object_name: bool = False,
    ) -> None:
        """Apply size and keep the badge overlay in sync with the preset."""
        self._base_button_size = QSize(widget_size)
        super()._apply_qta_size(
            widget_size,
            icon_size,
            preset=preset,
            use_legacy_object_name=use_legacy_object_name,
        )
        if self._badge is not None:
            self._badge.set_badge_size(self._preset_to_badge_size())
        self._refresh_button_footprint()

    def setText(self, text: str) -> None:  # type: ignore[override]
        """Override text."""
        self.setProperty("with_text", True)
        super().setText(text)

    def set_transparent(self, transparent: bool) -> None:
        """Set transparency."""
        from qtextra.helpers import polish_widget

        self.transparent = transparent
        polish_widget(self)

    def mousePressEvent(self, evt: QEvent) -> None:  # type: ignore[override]
        """Mouse press event."""
        if evt.button() == Qt.MouseButton.RightButton:  # type: ignore[attr-defined]
            self.on_right_click()
        elif evt.button() == Qt.MouseButton.LeftButton:  # type: ignore[attr-defined]
            self.on_click()
        super().mousePressEvent(evt)  # type: ignore[arg-type]

    def set_toggle_qta(self, name: str, checked_name: str, connect: bool = True, **kwargs: ty.Any) -> None:
        """Set changeable icon."""
        checked_kwargs = deepcopy(kwargs)

        name, kwargs_ = get_icon(name)
        kwargs.update(kwargs_)
        checked_name, checked_kwargs_ = get_icon(checked_name)
        checked_kwargs.update(checked_kwargs_)
        self._qta_data = (name, kwargs)
        self._checked_qta_data = (checked_name, checked_kwargs)
        color_ = kwargs.pop("color", None)
        color_ = checked_kwargs.pop("color", color_)
        color = color_ or self._icon_color or THEMES.get_hex_color("icon")
        icon = qtawesome.icon(
            checked_name if self.isChecked() else name,
            **self._checked_qta_data[1] if self.isChecked() else self._qta_data[1],
            color=color,
        )
        self.setIcon(icon)
        if connect:
            self.toggled.connect(self._on_toggle)

    def _on_toggle(self) -> None:
        """Update icons."""
        assert self._qta_data and self._checked_qta_data, "No qta data set."
        name = self._checked_qta_data[0] if self.isChecked() else self._qta_data[0]
        self._set_qta_icon(name, **self._checked_qta_data[1] if self.isChecked() else self._qta_data[1])

    def on_click(self) -> None:
        """Click event."""
        self.evt_click.emit(self)

    def on_right_click(self) -> None:
        """Right click event."""
        self.evt_right_click.emit(self)

    def connect_to_right_click(self, func: ty.Callable) -> None:
        """Connect function right right-click.

        It is not possible to check whether a function is connected to a signal so its better to use this function to
        connect via this function which leaves behind a flag so the paint event will add rectangle to the edge so the
        user knows there is a right-click menu available.
        """
        self.evt_right_click.connect(func)
        self.has_right_click = True
        hp.set_properties(self, {"right_click": True})

    def paintEvent(self, *args: ty.Any) -> None:
        """Paint event."""
        super().paintEvent(*args)
        if self.menu_enabled:
            self._paint_menu_corner()
        elif self.has_right_click:
            self._paint_right_click_corner()

    def _paint_corner(self, color: str) -> None:
        rect = self.rect()
        glyph_size = max(5, min(14, int(rect.width() * 0.25)))
        margin = max(1, rect.width() // 12)
        right = rect.width() - margin
        bottom = rect.height() - margin
        points = [
            QPointF(right, bottom - glyph_size),
            QPointF(right - glyph_size, bottom),
            QPointF(right, bottom),
        ]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = QColor(THEMES.get_hex_color(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF(points))

    def _paint_menu_corner(self) -> None:
        """Draw a small downward chevron in the bottom-right corner."""
        self._paint_corner("info")

    def _paint_right_click_corner(self) -> None:
        """Draw a filled triangular 'page-fold' in the bottom-right corner."""
        self._paint_corner("success")

    # Alias methods to offer Qt-like interface
    _onToggle = _on_toggle
    setCount = set_count
    setBadge = set_badge
    clearBadge = clear_badge
    setTransparent = set_transparent
    setToggleQta = set_toggle_qta
    onClick = on_click
    onRightClick = on_right_click
    connectToRightClick = connect_to_right_click


class QtTogglePushButton(QtImagePushButton):
    """Toggle button."""

    evt_toggled = Signal(bool)

    ICON_ON: str = ""
    ICON_OFF: str = ""

    _state: bool = False

    def __init__(self, *args, state: bool = False, auto_connect: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if auto_connect:
            self.auto_connect()
        self.state = state

    @property
    def state(self) -> bool:
        """Get state."""
        return self._state

    @state.setter
    def state(self, value: bool) -> None:
        changed = value != self._state
        self._state = value
        self.set_qta(self.ICON_ON if value else self.ICON_OFF)
        if changed:
            self.evt_toggled.emit(value)

    def set_state(self, state: bool, trigger: bool = True) -> None:
        """Set state."""
        with hp.qt_signals_blocked(self, block_signals=not trigger):
            self.state = state

    def auto_connect(self) -> None:
        """Automatically connect."""
        self.evt_click.connect(self.toggle_state)

    def toggle_state(self) -> None:
        """Toggle state."""
        self.state = not self.state

    # Alias methods to offer Qt-like interface
    setState = set_state
    autoConnect = auto_connect
    toggleState = toggle_state


class QtAnimationPlayButton(QtTogglePushButton):
    """Play button with multiple states to indicate current state."""

    ICON_ON = "stop"
    ICON_OFF = "start"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def playing(self) -> bool:
        """Get playing state."""
        return self.state

    @playing.setter
    def playing(self, state: bool) -> None:
        self.state = state


class QtPauseButton(QtTogglePushButton):
    """Play button with multiple states to indicate current state."""

    ICON_ON = "start"
    ICON_OFF = "pause"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def paused(self) -> bool:
        """Get playing state."""
        return self.state

    @paused.setter
    def paused(self, state: bool) -> None:
        self.state = state


class QtLockButton(QtTogglePushButton):
    """Lock button with open/closed state to indicate current state."""

    ICON_ON = "lock_closed"
    ICON_OFF = "lock_open"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def locked(self) -> bool:
        """Get playing state."""
        return self.state

    @locked.setter
    def locked(self, state: bool) -> None:
        self.state = state


class QtThemeButton(QtTogglePushButton):
    """Lock button with open/closed state to indicate current state."""

    ICON_ON = "dark_theme"
    ICON_OFF = "light_theme"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def dark(self) -> bool:
        """Get playing state."""
        return self.state

    @dark.setter
    def dark(self, state: bool) -> None:
        self.state = state


class QtAndOrButton(QtTogglePushButton):
    """Lock button with open/closed state to indicate current state."""

    ICON_ON = "and"
    ICON_OFF = "or"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def dark(self) -> bool:
        """Get playing state."""
        return self.state

    @dark.setter
    def dark(self, state: bool) -> None:
        self.state = state


class QtExpandButton(QtTogglePushButton):
    """Button that has chevron point up or down."""

    ICON_ON = "chevron_up"
    ICON_OFF = "chevron_down"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def expanded(self) -> bool:
        """Get state."""
        return self.state

    @expanded.setter
    def expanded(self, state: bool) -> None:
        self.state = state


class QtUnfoldButton(QtTogglePushButton):
    """Button that has chevron point up or down."""

    ICON_ON = "unfold_on"
    ICON_OFF = "unfold_off"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def expanded(self) -> bool:
        """Get state."""
        return self.state

    @expanded.setter
    def expanded(self, state: bool) -> None:
        self.state = state


class QtSortButton(QtTogglePushButton):
    """Button that has chevron point up or down."""

    ICON_ON = "sort_ascending"
    ICON_OFF = "sort_descending"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)


class QtToggleButton(QtTogglePushButton):
    """Lock button with open/closed state to indicate current state."""

    ICON_ON = "toggle_on"
    ICON_OFF = "toggle_off"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property  # type: ignore[override]
    def toggled(self) -> bool:
        """Get toggle state."""
        return self.state

    @toggled.setter
    def toggled(self, state: bool) -> None:
        self.state = state


class QtVerticalDirectionButton(QtTogglePushButton):
    """Lock button with open/closed state to indicate current state."""

    ICON_ON = "long_arrow_up"
    ICON_OFF = "long_arrow_down"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def up(self) -> bool:
        """Get toggle state."""
        return self.state

    @up.setter
    def up(self, state: bool) -> None:
        self.state = state

    @property
    def down(self) -> bool:
        """Get toggle state."""
        return not self.up


class QtHorizontalDirectionButton(QtTogglePushButton):
    """Lock button with open/closed state to indicate current state."""

    ICON_ON = "long_arrow_right"
    ICON_OFF = "long_arrow_left"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def right(self) -> bool:
        """Get toggle state."""
        return self.state

    @right.setter
    def right(self, state: bool) -> None:
        self.state = state

    @property
    def left(self) -> bool:
        """Get toggle state."""
        return not self.left


class QtVisibleButton(QtTogglePushButton):
    """A button with a shown/hidden icon."""

    ICON_ON = "visible_on"
    ICON_OFF = "visible_off"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def visible(self) -> bool:
        """Get toggle state."""
        return self.state

    @visible.setter
    def visible(self, state: bool) -> None:
        self.state = state

    @property
    def hidden(self) -> bool:
        """Get toggle state."""
        return not self.visible


class QtHiddenButton(QtTogglePushButton):
    """A button with hidden/shown icon."""

    ICON_ON = "visible_off"
    ICON_OFF = "visible_on"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def hidden(self) -> bool:
        """Get toggle state."""
        return self.state

    @hidden.setter
    def hidden(self, state: bool) -> None:
        self.state = state

    @property
    def visible(self) -> bool:
        """Get toggle state."""
        return not self.state


class QtFilterButton(QtTogglePushButton):
    """A button with filter on / filter off icon."""

    ICON_ON = "filter_on"
    ICON_OFF = "filter_off"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)


class QtPinButton(QtTogglePushButton):
    """Lock button with shown/hidden icon."""

    ICON_ON = "pin_on"
    ICON_OFF = "pin_off"

    def __init__(self, *args: ty.Any, color: bool = False, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        if color:
            self.ICON_ON = "pin_on_color"
            self.ICON_OFF = "pin_off_color"

    @property
    def pin(self) -> bool:
        """Get toggle state."""
        return self.state

    @pin.setter
    def pin(self, state: bool) -> None:
        self.state = state


class QtFullscreenButton(QtTogglePushButton):
    """Lock button with shown/hidden icon."""

    ICON_ON = "fullscreen"
    ICON_OFF = "maximize"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def fullscreen(self) -> bool:
        """Get toggle state."""
        return self.state

    @fullscreen.setter
    def fullscreen(self, state: bool) -> None:
        self.state = state


class QtMinimizeButton(QtTogglePushButton):
    """Lock button with shown/hidden icon."""

    ICON_ON = "minimize"
    ICON_OFF = "maximize"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    @property
    def minimized(self) -> bool:
        """Get toggle state."""
        return self.state

    @minimized.setter
    def minimized(self, state: bool) -> None:
        self.state = state


class QtBoolButton(QtTogglePushButton):
    """Boolean button."""

    ICON_ON = "true"
    ICON_OFF = "false"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)


class QtImageButton(QtTogglePushButton):
    """Boolean button."""

    ICON_ON = "images"
    ICON_OFF = "image"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)


class QtMaskButton(QtTogglePushButton):
    """Boolean button."""

    ICON_ON = "masks"
    ICON_OFF = "mask"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)


class QtNDisplayButton(QtTogglePushButton):
    """Boolean button."""

    ICON_ON = "2d"
    ICON_OFF = "3d"

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)


class QtMultiStatePushButton(QtImagePushButton):
    """Base class for a multi-state button where options are shown as a QMenu."""

    DEFAULT_STATE: str = ""
    STATE_TO_ICON: ty.ClassVar[dict[str, str]]
    STATE_TO_OPTION: ty.ClassVar[dict[str, str]]

    evt_changed = Signal(str)

    _state: str = ""
    _menu: QWidget | None
    _auto_show_menu_on_hover: bool

    def __init__(self, *args: ty.Any, auto_show_menu_on_hover: bool = True, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self._menu = None
        self._auto_show_menu_on_hover = auto_show_menu_on_hover
        self.setMouseTracking(True)
        default_state = self.get_default_state()
        if default_state:
            self.state = default_state

    def get_default_state(self) -> str:
        """Return the initial state for the button."""
        return self.DEFAULT_STATE

    def get_state_to_icon(self) -> dict[str, str]:
        """Return the state-to-icon mapping."""
        return self.STATE_TO_ICON

    def get_state_to_option(self) -> dict[str, str]:
        """Return the state-to-label mapping."""
        return self.STATE_TO_OPTION

    @property
    def state(self) -> str:
        """Get playing state."""
        return self._state

    @state.setter
    def state(self, state: str) -> None:
        self._state = state
        self.set_qta(self.get_state_to_icon()[state])
        self.evt_changed.emit(state)

    def set_state(self, state: str) -> None:
        """Set state."""
        self.state = state

    def set_auto_show_menu_on_hover(self, enabled: bool) -> None:
        """Enable or disable automatically showing the menu when hovering."""
        self._auto_show_menu_on_hover = enabled

    def set_and_show_menu(self) -> None:
        """Set menu."""
        state_to_option = self.get_state_to_option()
        state_to_icon = self.get_state_to_icon()
        menu = hp.make_menu(self)
        for state, label in state_to_option.items():
            hp.make_menu_item(
                self,
                label,
                icon=state_to_icon[state],
                func=partial(self.set_state, state=state),
                menu=menu,
            )
        self._menu = menu
        hp.show_below_widget(menu, self, x_offset=20)

    def on_click(self) -> None:
        """Show the state menu on click when auto-hover is disabled."""
        if not self._auto_show_menu_on_hover:
            QTimer.singleShot(0, self.set_and_show_menu)
        super().on_click()

    def enterEvent(self, event: QEnterEvent | QEvent) -> None:  # type: ignore[override]
        """Handle hover entry and show the state menu when enabled."""
        if self._auto_show_menu_on_hover:
            self.set_and_show_menu()
        if isinstance(event, QEnterEvent):
            super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Event."""
        if self._auto_show_menu_on_hover and self._menu is not None:
            self._menu.close()
            self._menu = None
        super().leaveEvent(event)

    # Alias methods to offer Qt-like interface
    setAndShowMenu = set_and_show_menu
    setAutoShowMenuOnHover = set_auto_show_menu_on_hover
    setState = set_state


class QtPriorityButton(QtMultiStatePushButton):
    """Priority button."""

    DEFAULT_STATE = "normal"
    STATE_TO_ICON: ty.ClassVar[dict[str, str]] = {
        "low": "priority_low",
        "normal": "priority_normal",
        "high": "priority_high",
    }
    STATE_TO_OPTION: ty.ClassVar[dict[str, str]] = {"low": "Low", "normal": "Normal", "high": "High"}

    @property
    def priority(self) -> str:
        """Get playing state."""
        return self.state

    @priority.setter
    def priority(self, state: str) -> None:
        self.state = state


class QtStateButton(QtMultiStatePushButton):
    """State button."""

    DEFAULT_STATE = "info"
    STATE_TO_ICON: ty.ClassVar[dict[str, str]] = {
        "success": "success",
        "debug": "debug",
        "info": "info",
        "warning": "warning",
        "error": "error",
    }
    STATE_TO_OPTION: ty.ClassVar[dict[str, str]] = {
        "success": "Success",
        "debug": "Debug",
        "info": "Info",
        "warning": "Warning",
        "error": "Error",
    }


class QtEmotionButton(QtMultiStatePushButton):
    """State button."""

    DEFAULT_STATE = "happy"
    STATE_TO_ICON: ty.ClassVar[dict[str, str]] = {
        "happy": "happy",
        "neutral": "neutral",
        "sad": "sad",
    }
    STATE_TO_OPTION: ty.ClassVar[dict[str, str]] = {
        "happy": "Happy!",
        "neutral": "Neutral",
        "sad": "Sad",
    }


class QtMultiThemeButton(QtMultiStatePushButton):
    """Theme button button."""

    ICON_ON = "dark_theme"
    ICON_OFF = "light_theme"

    def __init__(self, *args: ty.Any, auto_connect: bool = False, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        THEMES.evt_theme_added.connect(self._sync_state_from_theme)
        THEMES.evt_theme_changed.connect(self._sync_state_from_theme)
        self._sync_state_from_theme()
        if auto_connect:
            self.auto_connect()

    def get_default_state(self) -> str:
        """Return the current global theme as the initial state."""
        return THEMES.theme

    def get_state_to_option(self) -> dict[str, str]:
        """Build menu labels for all available themes."""
        return {theme: theme.replace("_", " ").title() for theme in THEMES.available_themes()}

    def get_state_to_icon(self) -> dict[str, str]:
        """Use light/dark icons based on the theme type."""
        return {
            theme: "dark_theme" if THEMES[theme].type == "dark" else "light_theme"
            for theme in THEMES.available_themes()
        }

    def _sync_state_from_theme(self) -> None:
        """Keep the button icon in sync with the active theme."""
        theme = THEMES.theme
        state_to_icon = self.get_state_to_icon()
        if theme not in state_to_icon:
            return
        with hp.qt_signals_blocked(self):
            self.state = theme

    def auto_connect(self) -> None:
        """Automatically apply the selected theme."""
        self.evt_changed.connect(THEMES.set_theme)


class QtToolbarPushButton(QtImagePushButton):
    """Image button."""

    START_OPACITY = 1.0
    END_OPACITY = 0.2
    PULSE_RATE = 1000
    N_LOOPS = 5

    indicator: str = ""
    _title: str = ""
    _text: str = ""
    _tooltip = None
    _suppress_hover_tooltip = False
    # set by a wrapper (e.g. `QtLabelledToolbarPushButton`) that drives hover tooltips for the whole tile
    _tooltip_target: QWidget | None = None

    panel_widget: QWidget | None = None
    about_widget: QWidget | None = None

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)

        self.opacity = QGraphicsOpacityEffect()
        self.opacity.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity)
        self.opacity_anim = QPropertyAnimation(self.opacity, b"opacity", self)
        self.opacity_anim.currentLoopChanged.connect(self._loop_update)
        self.opacity_anim.finished.connect(self.stop_pulse)

        self.tooltip_timer = hp.make_periodic_timer(self, self._show_tooltip, 700, start=False)
        self.tooltip_timer.setSingleShot(True)

        self.evt_click.connect(self.stop_pulse)
        self.evt_click.connect(self._suppress_tooltip_until_leave)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Use the configured button footprint when laying out toolbars."""
        return QSize(self._base_button_size)

    def setCheckable(self, checkable: bool) -> None:  # type: ignore[override]
        """Set checkable state and re-apply `[checkable=...]` stylesheet selectors."""
        changed = checkable != self.isCheckable()
        super().setCheckable(checkable)
        if changed:
            hp.polish_widget(self)

    def setToolTip(self, text: str) -> None:  # type: ignore[override]
        """Override tooltip."""
        self._text = text

    def setRichToolTip(self, title: str, content: str) -> None:
        """Override tooltip."""
        self._title = title
        self._text = content

    def _get_position(self) -> QPoint:
        target = self._tooltip_target or self
        pos = target.mapToGlobal(target.rect().topRight())
        pos -= QPoint(0, 22)
        return pos

    def _on_tooltip_closed(self) -> None:
        """Reset tooltip reference when closed externally (e.g. via close button)."""
        self._tooltip = None

    def _suppress_tooltip_until_leave(self) -> None:
        """Disable hover tooltips until the cursor leaves the button."""
        self._suppress_hover_tooltip = True
        self.tooltip_timer.stop()
        hp.close_widget(self._tooltip)
        self._tooltip = None

    def _show_tooltip(self) -> None:
        """Show a tooltip if it's available."""
        if not self._text or self._tooltip is not None or self._suppress_hover_tooltip:
            return
        try:
            self._tooltip = QtRichToolTip.show_tooltip(
                title=self._title,
                content=self._text,
                target=self._tooltip_target or self,
                parent=hp.get_main_window(self),
            )
            self._tooltip.destroyed.connect(self._on_tooltip_closed)
        except AttributeError:
            QToolTip.showText(self._get_position(), self._text, self)

    def _on_hover_enter(self) -> None:
        """Start the delayed hover tooltip."""
        if not self._tooltip and not self._suppress_hover_tooltip:
            self.tooltip_timer.start()

    def _on_hover_leave(self) -> None:
        """Cancel or close the hover tooltip."""
        self._suppress_hover_tooltip = False
        self.tooltip_timer.stop()
        hp.close_widget(self._tooltip)
        self._tooltip = None

    def event(self, evt: QEvent) -> bool:  # type: ignore[override]
        """Override event handler to quickly display/hide a tooltip."""
        # when wrapped, the wrapper drives hover so moving between icon and label keeps the tooltip
        if self._tooltip_target is None:
            if evt.type() == QEvent.Type.Enter:
                self._on_hover_enter()
                evt.ignore()
            elif evt.type() == QEvent.Type.Leave:
                self._on_hover_leave()
        return super().event(evt)

    @Slot(int)  # type: ignore[misc]
    def _loop_update(self, loop: int) -> None:
        """Reverse pulse direction for nicer visual effect."""
        start, end = (self.START_OPACITY, self.END_OPACITY) if loop % 2 == 0 else (self.END_OPACITY, self.START_OPACITY)
        self.opacity_anim.setStartValue(start)
        self.opacity_anim.setEndValue(end)

    @Slot(str)  # type: ignore[misc]
    @Slot(str, str)  # type: ignore[misc]
    def set_indicator(self, indicator_type: str, about: str | None = None) -> None:
        """Set indicator type."""
        assert indicator_type in [
            "",
            "success",
            "warning",
            "active",
        ], f"Cannot use `{indicator_type}` type of indicator."
        if not self.isCheckable():
            indicator_type = ""
        self.indicator = indicator_type
        self.start_pulse() if self.indicator else self.stop_pulse()

    @property
    def indicator_color(self) -> QColor:
        """Indicator color."""
        return QColor(THEMES.get_hex_color(INDICATOR_TYPES[self.indicator]))

    @property
    def edge_color(self) -> QColor:
        """Edge color."""
        return QColor(THEMES.get_hex_color(INDICATOR_TYPES[self.indicator]))

    def paintEvent(self, *args: ty.Any) -> None:
        """Paint event."""
        # default paint
        QPushButton.paintEvent(self, *args)

        if self.indicator and not self.isChecked():
            width = int(self.rect().width() / 6)
            radius = int(self.rect().width() / 10)
            pos = QPoint(self.rect().width() - width, width)

            paint = QPainter(self)
            pen = paint.pen()
            pen.setColor(self.edge_color)
            brush = QBrush(self.indicator_color)
            paint.setBrush(brush)
            paint.setPen(pen)
            paint.drawEllipse(pos, radius, radius)

    def start_pulse(self) -> None:
        """Start pulsating."""
        if self.indicator and not self.isChecked():
            self.opacity_anim.setEasingCurve(QEasingCurve.Type.Linear)
            self.opacity_anim.setDuration(self.PULSE_RATE)
            self.opacity_anim.setStartValue(self.START_OPACITY)
            self.opacity_anim.setEndValue(self.END_OPACITY)
            self.opacity_anim.setLoopCount(self.N_LOOPS)
            self.opacity_anim.start()

    def stop_pulse(self) -> None:
        """Stop pulsating."""
        self.opacity_anim.stop()
        self.opacity.setOpacity(1.0)

    # Alias methods to offer Qt-like interface
    setIndicator = set_indicator
    _getPosition = _get_position
    startPulse = start_pulse
    stopPulse = stop_pulse


class QtLabelledToolbarPushButton(QWidget):
    """A push button with a label.

    The wrapper owns the hover and active (checked) styling so that the icon and the label are highlighted
    together. The active state is exposed to stylesheets through the `active` dynamic property.
    """

    LABEL_SPACING = 0

    def __init__(self, *args: ty.Any, elide: bool = True, **kwargs: ty.Any):
        self._label_hidden = False
        self._label_text = ""
        self._elide = elide
        # width assigned to the tile by its owner (e.g. the toolbar's width sync); elided labels may use all of it
        self._elide_width = 0
        super().__init__(*args, **kwargs)
        # paint QSS background/border on this plain QWidget subclass and repaint on hover
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setProperty("active", False)

        self.image_btn = QtToolbarPushButton()
        self.image_btn.toggled.connect(self._sync_active_state)
        # the wrapper drives hover tooltips and pulses so icon and label behave as one tile
        self.image_btn._tooltip_target = self
        self.setGraphicsEffect(self.image_btn.opacity)  # moves the effect from the icon to the whole tile

        self.label = QLabel()
        self.label.setObjectName("toolbar_label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.label.setWordWrap(False)
        self.label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.LABEL_SPACING)
        layout.addWidget(self.image_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # Forwarded `QtToolbarPushButton` API, so the panel can treat both button types the same way
    @property
    def evt_click(self) -> Signal:
        """Signal emitted when the button is clicked."""
        return self.image_btn.evt_click

    @property
    def evt_right_click(self) -> Signal:
        """Signal emitted when the button is right-clicked."""
        return self.image_btn.evt_right_click

    def set_qta(self, name: str | tuple[str, dict], **kwargs: ty.Any) -> None:
        """Set the qtawesome icon."""
        self.image_btn.set_qta(name, **kwargs)

    def set_qta_size(self, size: int | QSize | tuple[int, int]) -> None:
        """Set the icon size."""
        self.image_btn.set_qta_size(size)

    def icon(self) -> QIcon:
        """Return the button icon."""
        return self.image_btn.icon()

    def setText(self, text: str) -> None:
        """Set the text drawn on the icon button."""
        self.image_btn.setText(text)

    def setToolTip(self, text: str) -> None:  # type: ignore[override]
        """Set the hover tooltip shown for the whole tile."""
        self.image_btn.setToolTip(text)

    def setRichToolTip(self, title: str, content: str) -> None:
        """Set the rich hover tooltip shown for the whole tile."""
        self.image_btn.setRichToolTip(title, content)

    def set_indicator(self, indicator_type: str, about: str | None = None) -> None:
        """Set indicator type."""
        self.image_btn.set_indicator(indicator_type, about)

    def start_pulse(self) -> None:
        """Start pulsating the whole tile."""
        self.image_btn.start_pulse()

    def stop_pulse(self) -> None:
        """Stop pulsating."""
        self.image_btn.stop_pulse()

    def setCheckable(self, checkable: bool) -> None:
        """Set whether the button is checkable."""
        self.image_btn.setCheckable(checkable)

    def isCheckable(self) -> bool:
        """Return whether the button is checkable."""
        return self.image_btn.isCheckable()

    def isChecked(self) -> bool:
        """Return whether the button is checked."""
        return self.image_btn.isChecked()

    def setChecked(self, checked: bool) -> None:
        """Set the checked state and keep the wrapper highlight in sync."""
        self.image_btn.setChecked(checked)
        # `toggled` is not emitted when the inner button's signals are blocked
        self._sync_active_state()

    def click(self) -> None:
        """Programmatically click the icon button."""
        self.image_btn.click()

    @property
    def has_right_click(self) -> bool:
        """Return whether a right-click handler was connected via `connect_to_right_click`."""
        return self.image_btn.has_right_click

    def connect_to_right_click(self, func: ty.Callable) -> None:
        """Connect function to right-click on the icon or label."""
        self.image_btn.connect_to_right_click(func)

    def on_click(self) -> None:
        """Emit `evt_click` as a pointer press would."""
        self.image_btn.on_click()

    def _sync_active_state(self, *_: ty.Any) -> None:
        """Mirror the inner button checked state onto the `active` property used by stylesheets."""
        active = self.image_btn.isChecked()
        if self.property("active") != active:
            self.setProperty("active", active)
            hp.polish_widget(self)

    def event(self, evt: QEvent) -> bool:  # type: ignore[override]
        """Show the hover tooltip while the cursor is anywhere over the icon or label."""
        if evt.type() == QEvent.Type.Enter:
            self.image_btn._on_hover_enter()
        elif evt.type() == QEvent.Type.Leave:
            self.image_btn._on_hover_leave()
        return super().event(evt)

    def mousePressEvent(self, evt: QEvent) -> None:  # type: ignore[override]
        """Forward presses on the label (or padding) to the icon button, matching `QtImagePushButton`."""
        if evt.button() == Qt.MouseButton.LeftButton:  # type: ignore[attr-defined]
            self.image_btn.on_click()
        elif evt.button() == Qt.MouseButton.RightButton:  # type: ignore[attr-defined]
            self.image_btn.on_right_click()
        super().mousePressEvent(evt)  # type: ignore[arg-type]

    @property
    def label_hidden(self) -> bool:
        """Get label hidden state."""
        return self._label_hidden

    @label_hidden.setter
    def label_hidden(self, value: bool) -> None:
        self._label_hidden = value
        self.label.setHidden(value)
        self.updateGeometry()

    def set_label(self, text: str) -> None:
        """Set label."""
        self._label_text = text
        self._update_label_geometry()
        self.updateGeometry()

    @property
    def elide(self) -> bool:
        """Get elide state."""
        return self._elide

    @elide.setter
    def elide(self, value: bool) -> None:
        self._elide = value
        self._update_label_geometry()
        self.updateGeometry()

    def set_default_size(
        self,
        xxsmall: bool = False,
        xsmall: bool = False,
        small: bool = False,
        normal: bool = False,
        average: bool = False,
        medium: bool = False,
        large: bool = False,
        xlarge: bool = False,
        xxlarge: bool = False,
    ) -> None:
        """Size the icon button and keep the label layout in sync."""
        if not any((xxsmall, xsmall, small, normal, average, medium, large, xlarge, xxlarge)):
            self._update_label_geometry()
            self.updateGeometry()
            return
        warnings.warn(
            "`set_default_size` is deprecated, use `set_qta_size_preset` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.image_btn.set_default_size(
            xxsmall=xxsmall,
            xsmall=xsmall,
            small=small,
            normal=normal,
            average=average,
            medium=medium,
            large=large,
            xlarge=xlarge,
            xxlarge=xxlarge,
        )
        self._update_label_geometry()
        self.updateGeometry()

    def set_qta_size_preset(self, preset: QtaSizePreset) -> None:
        """Set a named qta size preset and keep the label layout in sync."""
        self.image_btn.set_qta_size_preset(preset)
        self._update_label_geometry()
        self.updateGeometry()

    def _update_label_geometry(self) -> None:
        """Constrain the label so toolbar buttons stay compact.

        Elided labels never widen the tile: they use the icon width, or the tile width once the owner (e.g. the
        toolbar) made the tile wider, and are only elided when the text does not fit in that width.
        """
        text = self._label_text.strip()
        if not text:
            self.label.clear()
            self.label.setFixedSize(0, 0)
            return

        metrics = self.label.fontMetrics()
        lines = text.splitlines() or [text]
        icon_width = self.image_btn.sizeHint().width()
        natural_width = max(metrics.horizontalAdvance(line) for line in lines) + 2

        if self._elide:
            width = max(icon_width, min(self._elide_width, natural_width))
            display_text = "\n".join(metrics.elidedText(line, Qt.TextElideMode.ElideRight, width) for line in lines)
        else:
            width = max(icon_width, natural_width)
            display_text = "\n".join(lines)

        self.label.setText(display_text)
        self.label.setFixedWidth(width)
        self.label.ensurePolished()
        self.label.setFixedHeight(self.label.sizeHint().height())

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Keep toolbar buttons narrow even when labels are long."""
        icon_size = self.image_btn.sizeHint()
        if self._label_hidden or not self._label_text.strip():
            return QSize(icon_size.width(), icon_size.height())

        spacing = self.layout().spacing() if self.layout() is not None else 0
        # elided labels follow the tile width, so they must not feed back into the requested width
        width = icon_size.width() if self._elide else max(icon_size.width(), self.label.width())
        height = icon_size.height() + spacing + self.label.height()
        return QSize(width, height)

    def resizeEvent(self, evt: QResizeEvent) -> None:  # type: ignore[override]
        """Re-elide the label when the tile width changes."""
        super().resizeEvent(evt)
        if self._elide and evt.size().width() != self._elide_width:
            self._elide_width = evt.size().width()
            self._update_label_geometry()

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        """Match the constrained size hint."""
        return self.sizeHint()

    # Alias methods to offer Qt-like interface
    setDefaultSize = set_default_size
    setQtaSizePreset = set_qta_size_preset
    setLabel = set_label


#: Either toolbar button flavour; both expose the same forwarded API.
ToolbarButton: ty.TypeAlias = QtToolbarPushButton | QtLabelledToolbarPushButton

if __name__ == "__main__":  # pragma: no cover
    import sys

    val = True

    def _main() -> None:  # type: ignore[no-untyped-def]
        from qtextra.assets import QTA_MAPPING
        from qtextra.utils.dev import qframe

        def _disable_toolbar_labels():
            nonlocal toolbar_buttons

            for btn in toolbar_buttons:
                btn.label_hidden = not btn.label_hidden

        toolbar_buttons = []

        app, frame, va = qframe(False)
        frame.setMinimumSize(800, 800)

        ha = QHBoxLayout()
        ha.addWidget(hp.make_btn(frame, "Toggle toolbar label visibility", func=_disable_toolbar_labels))
        va.addLayout(ha)

        ha = QHBoxLayout()
        va.addLayout(ha)

        lay = QVBoxLayout()
        ha.addLayout(lay)

        btn2 = QtImagePushButton(parent=frame)
        btn2.setObjectName("info")
        lay.addWidget(btn2)

        lay.addWidget(QtAnimationPlayButton(parent=frame, auto_connect=True))
        lay.addWidget(QtPauseButton(parent=frame, auto_connect=True))
        lay.addWidget(QtImageButton(parent=frame, auto_connect=True))
        lay.addWidget(QtMaskButton(parent=frame, auto_connect=True))
        lay.addWidget(QtNDisplayButton(parent=frame, auto_connect=True))
        lay.addWidget(QtLockButton(parent=frame, auto_connect=True))
        lay.addWidget(QtHorizontalDirectionButton(parent=frame, auto_connect=True))
        lay.addWidget(QtVisibleButton(parent=frame, auto_connect=True))
        lay.addWidget(QtHiddenButton(parent=frame, auto_connect=True))
        lay.addWidget(QtFilterButton(parent=frame, auto_connect=True))
        lay.addWidget(QtVerticalDirectionButton(parent=frame, auto_connect=True))
        lay.addWidget(QtToggleButton(parent=frame, auto_connect=True))
        lay.addWidget(QtExpandButton(parent=frame, auto_connect=True))
        lay.addWidget(QtUnfoldButton(parent=frame, auto_connect=True))
        lay.addWidget(QtSortButton(parent=frame, auto_connect=True))
        lay.addWidget(QtPinButton(parent=frame, auto_connect=True))
        lay.addWidget(QtFullscreenButton(parent=frame, auto_connect=True))
        lay.addWidget(QtMinimizeButton(parent=frame, auto_connect=True))
        lay.addWidget(QtThemeButton(parent=frame, auto_connect=True))
        lay.addWidget(QtBoolButton(parent=frame, auto_connect=True))
        lay.addWidget(QtAndOrButton(parent=frame, auto_connect=True))

        # multi-state
        lay.addWidget(QtPriorityButton(parent=frame, auto_connect=True))
        lay.addWidget(QtStateButton(parent=frame, auto_connect=True))
        lay.addWidget(QtEmotionButton(parent=frame, auto_connect=True))
        lay.addWidget(QtMultiThemeButton(parent=frame, auto_connect=True, auto_show_menu_on_hover=False))

        ha.addWidget(hp.make_v_line())

        lay = QVBoxLayout()

        def _print_right_click() -> None:
            print("Right click")

        for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
            btn = QtImagePushButton()
            btn.set_qta_size_preset("large")
            if i % 2 == 0:
                btn.connect_to_right_click(_print_right_click)
            if i % 3 == 0:
                btn.set_count(i)
            if i % 5 == 0:
                btn.menu_enabled = True
            btn.set_qta(qta_name, scale_factor=1)
            btn.setToolTip(f"{name} :: {qta_name}")
            btn.setCheckable(True)
            lay.addWidget(btn)
            if i % 10 == 0:
                ha.addLayout(lay)
                lay = QVBoxLayout()
        ha.addWidget(hp.make_v_line())

        # lay = QVBoxLayout()
        # for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
        #     btn = QtToolbarPushButton()
        #     btn.set_qta(qta_name)
        #     btn.set_qta_size_preset("large")
        #     btn.setToolTip(f"{name} :: {qta_name}")
        #     lay.addWidget(btn)
        #     if i % 10 == 0:
        #         ha.addLayout(lay)
        #         lay = QVBoxLayout()
        # ha.addWidget(hp.make_v_line())

        lay = QVBoxLayout()
        for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
            btn = QtLabelledToolbarPushButton()
            toolbar_buttons.append(btn)
            btn.set_qta(qta_name)
            btn.set_label(name)
            btn.setToolTip(f"{name} :: {qta_name}")
            lay.addWidget(btn)
            if i == 10:
                ha.addLayout(lay)
                break

        ha.addWidget(hp.make_v_line())

        lay = QVBoxLayout()
        for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
            btn = QtImagePushButton()
            btn.set_qta(qta_name)
            btn.setText(name)
            btn.setToolTip(f"{name} :: {qta_name}")
            lay.addWidget(btn)
            if i == 10:
                ha.addLayout(lay)
                break

        frame.show()
        sys.exit(app.exec_())

    _main()
