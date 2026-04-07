"""Custom image button class."""

from __future__ import annotations

import typing as ty
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
    QRectF,
    QSize,
    Qt,
    Signal,
    Slot,
)
from qtpy.QtGui import QBrush, QColor, QEnterEvent, QFont, QPainter
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
from qtextra.widgets._qta_mixin import QtaMixin
from qtextra.widgets.qt_tooltip import QtToolTip, TipPosition

INDICATOR_TYPES = {"success": "success", "warning": "warning", "active": "progress"}


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
        super().__init__()
        self.setProperty("transparent", False)
        self.transparent = False
        with suppress(RuntimeError):
            THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def set_count(self, count: int, enabled: bool = True) -> None:
        """Enable count indicator."""
        self.count = count
        self.count_enabled = enabled

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
        paint = QPainter(self)
        if self.has_right_click or self.menu_enabled:
            width = self.rect().width() / 6
            radius = self.rect().width() / 8
            x = self.rect().width() - width
            y = self.rect().height() - width
            color = THEMES.get_hex_color("success" if self.has_right_click else "highlight")
            paint.setPen(QColor(color))
            paint.setBrush(QColor(color))
            paint.drawEllipse(QPointF(x, y), radius, radius)

        if self.count_enabled:
            # add text
            text = "9+" if self.count > 9 else str(self.count)

            color = THEMES.get_hex_color("icon")
            paint.setPen(QColor(color))
            paint.setBrush(QColor(color))
            radius = self.rect().width() / 6
            x = self.rect().x()
            y = self.rect().y()
            rect = QRectF(x, y, radius * 4, radius * 4)
            font: QFont = paint.font()
            font.setPointSize(12)
            font.setBold(True)
            paint.setFont(font)
            paint.drawText(rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, text)

    # Alias methods to offer Qt-like interface
    _onToggle = _on_toggle
    setCount = set_count
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
    """Lock button with shown/hidden icon."""

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

    def enterEvent(self, event: QEnterEvent | QEvent) -> None:  # type: ignore[override]
        """Handle hover entry and show the state menu when enabled."""
        if self._auto_show_menu_on_hover:
            self.set_and_show_menu()
        if isinstance(event, QEnterEvent):
            super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Event."""
        if self._menu is not None:
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
    _text: str = ""
    _tooltip = None
    _suppress_hover_tooltip = False

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

    def setToolTip(self, text: str) -> None:  # type: ignore[override]
        """Override tooltip."""
        self._text = text

    def _get_position(self) -> QPoint:
        rect = self.rect()
        pos = self.mapToGlobal(rect.topRight())
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
            self._tooltip = QtToolTip.init(
                self,
                title="",
                content=self._text,
                icon=None,
                parent=self,
                tail_position=TipPosition.LEFT,
                is_closable=True,
                duration=-1,
            )
            self._tooltip.destroyed.connect(self._on_tooltip_closed)
        except AttributeError:
            # fallback to QToolTip if QtToolTip is not available
            QToolTip.showText(self._get_position(), self._text, self)

    def event(self, evt: QEvent) -> bool:  # type: ignore[override]
        """Override event handler to quickly display/hide a tooltip."""
        if evt.type() == QEvent.Type.Enter:
            if not self._tooltip and not self._suppress_hover_tooltip:
                self.tooltip_timer.start()
            evt.ignore()
        elif evt.type() == QEvent.Type.Leave:
            self._suppress_hover_tooltip = False
            self.tooltip_timer.stop()
            hp.close_widget(self._tooltip)
            self._tooltip = None
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
    """A push button with a label."""

    LABEL_SPACING = 0

    def __init__(self, *args: ty.Any, elide: bool = True, **kwargs: ty.Any):
        self._label_hidden = False
        self._label_text = ""
        self._elide = elide
        super().__init__(*args, **kwargs)

        self.image_btn = QtToolbarPushButton()
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

        # Add methods from the QtToolbarPushButton
        self.evt_click = self.image_btn.evt_click
        self.set_qta = self.image_btn.set_qta
        self.setText = self.image_btn.setText
        self.setChecked = self.image_btn.setChecked
        self.set_indicator = self.image_btn.set_indicator
        self.set_indicator = self.image_btn.set_indicator
        self.stop_pulse = self.image_btn.stop_pulse
        self.start_pulse = self.image_btn.start_pulse
        self.setCheckable = self.image_btn.setCheckable
        self.isChecked = self.image_btn.isChecked
        self.click = self.image_btn.click

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

    def _update_label_geometry(self) -> None:
        """Constrain the label so toolbar buttons stay compact."""
        text = self._label_text.strip()
        if not text:
            self.label.clear()
            self.label.setFixedSize(0, 0)
            return

        metrics = self.label.fontMetrics()
        lines = text.splitlines() or [text]
        icon_width = self.image_btn.sizeHint().width()

        if self._elide:
            width = icon_width
            display_text = "\n".join(metrics.elidedText(line, Qt.TextElideMode.ElideRight, width) for line in lines)
        else:
            width = max(icon_width, max(metrics.horizontalAdvance(line) for line in lines) + 2)
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
        width = max(icon_size.width(), self.label.width())
        height = icon_size.height() + spacing + self.label.height()
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        """Match the constrained size hint."""
        return self.sizeHint()

    # Alias methods to offer Qt-like interface
    setDefaultSize = set_default_size
    setLabel = set_label


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
        lay.addWidget(QtVerticalDirectionButton(parent=frame, auto_connect=True))
        lay.addWidget(QtToggleButton(parent=frame, auto_connect=True))
        lay.addWidget(QtExpandButton(parent=frame, auto_connect=True))
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
        lay.addWidget(QtMultiThemeButton(parent=frame, auto_connect=True))

        ha.addWidget(hp.make_v_line())

        lay = QVBoxLayout()

        def _print_right_click() -> None:
            print("Right click")

        for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
            btn = QtImagePushButton()
            if i % 2 == 0:
                btn.connect_to_right_click(_print_right_click)
            if i % 3 == 0:
                btn.set_count(i)
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
        #     btn.set_large()
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
