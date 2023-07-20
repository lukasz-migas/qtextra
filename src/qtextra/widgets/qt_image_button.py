"""Custom image button class."""
import typing as ty

import qtawesome
from qtpy.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, QSize, Qt, Signal, Slot
from qtpy.QtGui import QBrush, QColor, QPainter
from qtpy.QtWidgets import QGraphicsOpacityEffect, QPushButton, QToolTip

from qtextra.assets import get_icon
from qtextra.config import THEMES

INDICATOR_TYPES = {"success": "success", "warning": "warning", "active": "progress"}


class QtImagePushButton(QPushButton):
    """Image button."""

    evt_click = Signal(QPushButton)
    evt_right_click = Signal(QPushButton)
    has_right_click: bool = False

    _qta_data = None

    def __init__(self, *args, **kwargs):
        self._icon_color = kwargs.pop("icon_color_override", None)
        super().__init__(*args, **kwargs)
        self.setProperty("transparent", False)
        self.transparent = False
        THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def set_transparent(self, transparent: bool) -> None:
        """Set transparency."""
        from qtextra.helpers import polish_widget

        self.transparent = transparent
        polish_widget(self)

    def mousePressEvent(self, evt) -> None:
        """Mouse press event."""
        if evt.button() == Qt.RightButton:
            self.on_right_click()
        elif evt.button() == Qt.LeftButton:
            self.on_click()
        super().mousePressEvent(evt)

    def set_qta(self, name: str, **kwargs) -> None:
        """Set QtAwesome icon."""
        name = get_icon(name)
        self._qta_data = (name, kwargs)
        color = self._icon_color or THEMES.get_hex_color("icon")
        icon = qtawesome.icon(name, **self._qta_data[1], color=color)
        self.setIcon(icon)

    def set_size(self, size: ty.Tuple[int, int]) -> None:
        """Set maximum size of the icon."""
        size = QSize(*size)
        self.setMinimumSize(size)
        self.setMaximumSize(size)
        self.setIconSize(size)

    def set_small(self) -> None:
        """Set large font."""
        self.setObjectName("small_icon")
        self.setIconSize(QSize(16, 16))

    def set_normal(self) -> None:
        """Set medium font."""
        self.setObjectName("normal_icon")
        self.setIconSize(QSize(20, 20))

    def set_medium(self) -> None:
        """Set medium font."""
        self.setObjectName("medium_icon")
        self.setIconSize(QSize(28, 28))

    def set_large(self) -> None:
        """Set large font."""
        self.setObjectName("large_icon")
        self.setIconSize(QSize(32, 32))

    def set_xlarge(self) -> None:
        """Set large."""
        self.setObjectName("xlarge_icon")
        self.setIconSize(QSize(60, 60))

    def set_xxlarge(self) -> None:
        """Set large."""
        self.setObjectName("xxlarge_icon")
        self.setIconSize(QSize(80, 80))

    def set_xxxlarge(self) -> None:
        """Set large."""
        self.setObjectName("xxxlarge_icon")
        self.setIconSize(QSize(120, 120))

    def _update_qta(self) -> None:
        """Update qta icon."""
        if self._qta_data:
            name, kwargs = self._qta_data
            self.set_qta(name, **kwargs)

    def on_click(self) -> None:
        """Click event."""
        self.evt_click.emit(self)

    def on_right_click(self) -> None:
        """Right click event."""
        self.evt_right_click.emit(self)

    def connect_to_right_click(self, func) -> None:
        """Connect function right right-click.

        It is not possible to check whether a function is connected to a signal so its better to use this function to
        connect via this function which leaves behind a flag so the paint event will add rectangle to the edge so the
        user knows there is a right-click menu available.
        """
        self.evt_right_click.connect(func)
        self.has_right_click = True

    def paintEvent(self, *args) -> None:
        """Paint event."""
        # default paint
        super().paintEvent(*args)

        if self.has_right_click:
            width = self.rect().width() / 4
            rect = QRect()
            rect.moveTo(self.rect().width() - width, self.rect().height() - width)
            rect.setWidth(width)
            rect.setHeight(width)
            paint = QPainter(self)
            paint.fillRect(rect, QColor(THEMES.get_hex_color("text")))


class QtAnimationPlayButton(QtImagePushButton):
    """Play button with multiple states to indicate current state."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reverse = False
        self.reverse = False
        self._playing = False
        self.playing = False

    @property
    def playing(self) -> bool:
        """Get playing state."""
        return self._playing

    @playing.setter
    def playing(self, state: bool):
        self._playing = state
        self.set_qta("stop" if state else "start")

    @property
    def reverse(self) -> bool:
        """Get reverse state."""
        return self._reverse

    @reverse.setter
    def reverse(self, state: bool):
        from qtextra.helpers import polish_widget

        self._reverse = state
        self.set_qta("left_arrow" if state else "right_arrow")
        self.setProperty("reverse", str(state))
        polish_widget(self)


class QtPauseButton(QtImagePushButton):
    """Play button with multiple states to indicate current state."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paused = False
        self.paused = False

    @property
    def paused(self) -> bool:
        """Get playing state."""
        return self._paused

    @paused.setter
    def paused(self, state: bool) -> None:
        self._paused = state
        self.set_qta("start" if state else "pause")


class QtLockButton(QtImagePushButton):
    """Lock button with open/closed state to indicate current state."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locked = False
        self.locked = False

    def auto_connect(self):
        """Automatically connect."""
        self.evt_click.connect(self.toggle_lock)

    def toggle_lock(self):
        """Toggle lock."""
        self.locked = not self.locked

    @property
    def locked(self) -> bool:
        """Get playing state."""
        return self._locked

    @locked.setter
    def locked(self, state: bool):
        self._locked = state
        self.set_qta("lock_closed" if state else "lock_open")


class QtExpandButton(QtImagePushButton):
    """Button that has chevron point up or down."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expanded = False
        self.expanded = False

    @property
    def expanded(self) -> bool:
        """Get state."""
        return self._expanded

    @expanded.setter
    def expanded(self, state: bool):
        self._expanded = state
        self.set_qta("chevron_up" if state else "chevron_down")


class QtToggleButton(QtImagePushButton):
    """Lock button with open/closed state to indicate current state."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._toggled = False
        self.toggled = False

    @property
    def toggled(self) -> bool:
        """Get toggle state."""
        return self._toggled

    @toggled.setter
    def toggled(self, state: bool):
        self._toggled = state
        self.set_qta("toggle_on" if state else "toggle_off")


class QtDirectionButton(QtImagePushButton):
    """Lock button with open/closed state to indicate current state."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_up = False
        self.up = True

    @property
    def up(self) -> bool:
        """Get toggle state."""
        return self._is_up

    @up.setter
    def up(self, state: bool):
        self._is_up = state
        self.set_qta("arrow_up" if state else "arrow_down")

    @property
    def down(self) -> bool:
        """Get toggle state."""
        return not self._is_up


class QtVisibleButton(QtImagePushButton):
    """Lock button with shown/hidden icon."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_visible = False
        self.visible = True

    @property
    def visible(self) -> bool:
        """Get toggle state."""
        return self._is_visible

    @visible.setter
    def visible(self, state: bool):
        self._is_visible = state
        self.set_qta("visible" if state else "visible_off")

    @property
    def hidden(self) -> bool:
        """Get toggle state."""
        return not self._is_visible

    def toggle_state(self):
        """Toggle state between shown/hidden."""
        self.visible = not self.visible


class QtToolbarPushButton(QtImagePushButton):
    """Image button."""

    START_OPACITY = 1.0
    END_OPACITY = 0.2
    PULSE_RATE = 1000
    N_LOOPS = 5

    indicator: str = ""

    _widget = None
    _about_widget = None
    _text = ""

    # evt_hover = Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)

        self.opacity = QGraphicsOpacityEffect()
        self.opacity.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity)
        self.opacity_anim = QPropertyAnimation(self.opacity, b"opacity", self)
        self.opacity_anim.currentLoopChanged.connect(self._loop_update)
        self.opacity_anim.finished.connect(self.stop_pulse)

        self.evt_click.connect(self.stop_pulse)

    def setToolTip(self, text: str):
        """Override tooltip."""
        self._text = text

    def _get_position(self):
        rect = self.rect()
        pos = self.mapToGlobal(rect.topRight())
        pos -= QPoint(0, 22)
        return pos

    def event(self, evt):
        """Override event handler to quickly display/hide tooltip."""
        if evt.type() == QEvent.Enter:
            QToolTip.showText(self._get_position(), self._text)
            evt.ignore()
        elif evt.type() == QEvent.Leave:
            QToolTip.hideText()
        return super().event(evt)

    @Slot(int)
    def _loop_update(self, loop: int):
        """Reverse pulse direction for nicer visual effect."""
        start, end = (self.START_OPACITY, self.END_OPACITY) if loop % 2 == 0 else (self.END_OPACITY, self.START_OPACITY)
        self.opacity_anim.setStartValue(start)
        self.opacity_anim.setEndValue(end)

    @Slot(str)
    @Slot(str, str)
    def set_indicator(self, indicator_type: str, about: str = None):
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
        return QColor(THEMES.get_hex_color("background"))

    def paintEvent(self, *args):
        """Paint event."""
        # default paint
        QPushButton.paintEvent(self, *args)

        if self.indicator and not self.isChecked():
            width = self.rect().width() / 6
            pos = QPoint(self.rect().width() - width, width)

            paint = QPainter(self)
            pen = paint.pen()
            pen.setColor(self.edge_color)
            brush = QBrush(self.indicator_color)
            paint.setBrush(brush)
            paint.setPen(pen)
            paint.drawEllipse(pos, width, width)

    def start_pulse(self):
        """Start pulsating."""
        if self.indicator and not self.isChecked():
            self.opacity_anim.setEasingCurve(QEasingCurve.Linear)
            self.opacity_anim.setDuration(self.PULSE_RATE)
            self.opacity_anim.setStartValue(self.START_OPACITY)
            self.opacity_anim.setEndValue(self.END_OPACITY)
            self.opacity_anim.setLoopCount(self.N_LOOPS)
            self.opacity_anim.start()

    def stop_pulse(self):
        """Stop pulsating."""
        self.opacity_anim.stop()
        self.opacity.setOpacity(1.0)


if __name__ == "__main__":  # pragma: no cover
    val = True

    def _main():
        pass

        from qtextra.assets import QTA_MAPPING
        from qtextra.config.theme import THEMES
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qmain

        def _toggle_theme():
            THEMES.theme = choice(THEMES.available_themes())
            THEMES.set_theme_stylesheet(frame)

        def _check_pause():
            pause_btn.paused = not pause_btn.paused

        def _check_lock():
            lock_btn.locked = not lock_btn.locked

        def _check_play():
            play_btn.playing = not play_btn.playing

        app, frame, ha = qmain(True)
        frame.setMinimumSize(600, 600)

        lay = QHBoxLayout()
        ha.addLayout(lay)

        btn2 = make_btn(frame, "Click here to toggle theme")
        btn2.clicked.connect(_toggle_theme)
        lay.addWidget(btn2)

        btn2 = QtImagePushButton(parent=frame)
        btn2.setObjectName("info")
        lay.addWidget(btn2)
        play_btn = QtAnimationPlayButton(parent=frame)
        play_btn.clicked.connect(_check_play)
        lay.addWidget(play_btn)
        pause_btn = QtPauseButton(parent=frame)
        pause_btn.clicked.connect(_check_pause)
        lay.addWidget(pause_btn)
        lock_btn = QtLockButton(parent=frame)
        lock_btn.clicked.connect(_check_lock)
        lay.addWidget(lock_btn)

        lay = QVBoxLayout()
        for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
            label = QtImagePushButton()
            label.set_qta(qta_name, scale_factor=1)
            label.setToolTip(f"{name} :: {qta_name}")
            lay.addWidget(label)
            if i % 10 == 0:
                ha.addLayout(lay)
                lay = QVBoxLayout()

        lay = QVBoxLayout()
        for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
            label = QtToolbarPushButton()
            label.set_qta(qta_name)
            label.set_large()
            label.setToolTip(f"{name} :: {qta_name}")
            lay.addWidget(label)
            if i % 10 == 0:
                ha.addLayout(lay)
                lay = QVBoxLayout()

        frame.show()
        sys.exit(app.exec_())

    _main()
