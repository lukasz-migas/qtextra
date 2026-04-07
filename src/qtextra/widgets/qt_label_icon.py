"""QtIcon."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from koyo.typing import PathLike
from qtpy.QtCore import (  # type: ignore[attr-defined]  # type: ignore[attr-defined]
    QPointF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from qtpy.QtGui import QColor, QEnterEvent, QPainter, QPixmap, QResizeEvent
from qtpy.QtWidgets import QLabel, QToolTip, QWidget
from superqt.utils import qdebounced

from qtextra.config import THEMES
from qtextra.dialogs.qt_info_popup import InfoDialog
from qtextra.widgets._qta_mixin import QtaMixin


def make_png_label(icon_path: str, size: tuple[int, int] = (40, 40)) -> QLabel:
    """Make svg icon."""
    image = QtKeepAspectLabel(None, icon_path)
    image.setMinimumSize(*size)
    return image


class QtKeepAspectLabel(QLabel):
    """Keep the aspect ratio label."""

    def __init__(self, parent: QWidget | None, path: PathLike):
        super().__init__(parent)
        self.path = path
        self._setPixmap()

    @qdebounced(timeout=100, leading=False)
    def _setPixmap(self) -> None:
        img = QPixmap(self.path)
        size = self.size()
        pix = img.scaled(size, Qt.AspectRatioMode.KeepAspectRatio)
        self.setPixmap(pix)

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        """Resize event."""
        self._setPixmap()
        return super().resizeEvent(event)

    def setPath(self, path: PathLike) -> None:
        """Set path."""
        self.path = path
        self._setPixmap()


class QtActiveIcon(QLabel):
    """Active icon that shows activity."""

    def __init__(self, which: str = "infinity", size: tuple[int, int] = (20, 20), start: bool = False):
        from qtextra.helpers import make_gif

        super().__init__()
        self.setScaledContents(True)
        self._active = False

        self.loading_movie = make_gif(which, size=size, start=start)
        if size is not None:
            self.setMaximumSize(*size)
        self.setMovie(self.loading_movie)
        self.active = start

    @property
    def active(self) -> bool:
        """Get active state."""
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        """Set active state."""
        self._active = value
        self.loading_movie.start() if value else self.loading_movie.stop()
        self.show() if value else self.hide()

    def set_active(self, active: bool) -> None:
        """Set active state."""
        self.active = active

    # Alias methods to offer Qt-like interface
    setActive = set_active


class QtIconLabel(QLabel):
    """Label with icon."""

    evt_clicked = Signal()

    def __init__(self, object_name: str, *args, **kwargs):
        super().__init__()
        self.setMouseTracking(True)
        self.setObjectName(object_name)

    def mousePressEvent(self, ev):
        """Mouse press event."""
        if ev.button() == Qt.MouseButton.LeftButton:
            self.evt_clicked.emit()
        super().mousePressEvent(ev)


class QtQtaLabel(QtIconLabel, QtaMixin):
    """Label."""

    _icon = None

    def __init__(
        self,
        *args,
        xxsmall: bool = False,
        xsmall: bool = False,
        small: bool = False,
        normal: bool = False,
        average: bool = False,
        medium: bool = False,
        large: bool = False,
        xlarge: bool = False,
        xxlarge: bool = False,
        **kwargs,
    ):
        super().__init__("", *args, **kwargs)
        self._size = QSize(28, 28)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        self.set_default_size(
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
        with suppress(RuntimeError):
            THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def setIcon(self, _icon) -> None:
        """Update icon."""
        self._icon = _icon
        self.setPixmap(_icon.pixmap(self._size))

    def setIconSize(self, size: QSize) -> None:
        """Set icon size."""
        self._size = size
        self.update()

    def update(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        """Update label."""
        if self._icon:
            self.setPixmap(self._icon.pixmap(self._size))
        return super().update(*args, **kwargs)


class QtWarningPulseLabel(QtQtaLabel):
    """A warning icon label that pulses indefinitely."""

    def __init__(self, interval: int = 1000):
        super().__init__(large=True)
        self._base_size = 32
        self._pulse_delta = 8
        self._pulse_animation = QVariantAnimation(self)
        self._pulse_animation.setStartValue(0.0)
        self._pulse_animation.setKeyValueAt(0.5, 1.0)
        self._pulse_animation.setEndValue(0.0)
        self._pulse_animation.setDuration(interval)
        self._pulse_animation.setLoopCount(-1)
        self._pulse_animation.valueChanged.connect(self._on_pulse)

        self.set_qta("warning", color=THEMES.get_hex_color("warning"))
        self.setToolTip("Warning icon with an indefinite pulse")
        self.setIconSize(QSize(self._base_size, self._base_size))
        self._pulse_animation.start()

    def _on_pulse(self, value: float) -> None:
        size = self._base_size + round(self._pulse_delta * value)
        self.setIconSize(QSize(size, size))


class QtPulsingAttentionLabel(QtQtaLabel):
    """An icon label that pulses between two colors to draw user attention.

    The icon smoothly interpolates from `color_from` to `color_to` and back,
    completing one full cycle every `interval_ms` milliseconds.

    Use `start_pulsing()` / `stop_pulsing()` to control the animation at
    runtime — e.g. start when a condition requires attention and stop once
    the user has acknowledged it.

    Example usage::

        label = QtPulsingAttentionLabel(
            qta_name="warning",
            color_from_key="warning",
            color_to_key="icon",
        )
        label.setToolTip("Needs your attention!")
        layout.addWidget(label)
    """

    def __init__(
        self,
        qta_name: str = "warning",
        color_from_key: str = "warning",
        color_to_key: str = "icon",
        interval: int = 1000,
        **kwargs: ty.Any,
    ):
        super().__init__(large=True, **kwargs)
        self._color_from_key = color_from_key
        self._color_to_key = color_to_key
        self._color_from = QColor(THEMES.get_hex_color(color_from_key))
        self._color_to = QColor(THEMES.get_hex_color(color_to_key))

        self._pulse_animation = QVariantAnimation(self)
        self._pulse_animation.setStartValue(0.0)
        self._pulse_animation.setKeyValueAt(0.5, 1.0)
        self._pulse_animation.setEndValue(0.0)
        self._pulse_animation.setDuration(interval)
        self._pulse_animation.setLoopCount(-1)
        self._pulse_animation.valueChanged.connect(self._on_pulse)

        self.set_qta(qta_name, color=self._color_from.name())
        self._pulse_animation.start()

    def _refresh_colors(self) -> None:
        """Re-read colors from the active theme."""
        self._color_from = QColor(THEMES.get_hex_color(self._color_from_key))
        self._color_to = QColor(THEMES.get_hex_color(self._color_to_key))

    def _update_qta(self) -> None:
        """Refresh colors from the active theme, then update the icon."""
        self._refresh_colors()
        super()._update_qta()

    def _on_pulse(self, value: float) -> None:
        r = int(self._color_from.red() + (self._color_to.red() - self._color_from.red()) * value)
        g = int(self._color_from.green() + (self._color_to.green() - self._color_from.green()) * value)
        b = int(self._color_from.blue() + (self._color_to.blue() - self._color_from.blue()) * value)
        color = QColor(r, g, b)
        if self._qta_data:
            name, kws = self._qta_data
            self._set_icon(name, **kws, color=color.name())

    def pulse(self, state: bool) -> None:
        """Enable or disable the pulse animation."""
        if state:
            self.start_pulsing()
        else:
            self.stop_pulsing()

    def start_pulsing(self) -> None:
        """Start the pulse animation."""
        self._pulse_animation.start()

    def stop_pulsing(self) -> None:
        """Stop the pulse animation and restore the base color."""
        self._pulse_animation.stop()
        if self._qta_data:
            name, kws = self._qta_data
            self._set_icon(name, **kws, color=self._color_from.name())


class QtQtaNotificationLabel(QtQtaLabel):
    """Label with a small dot to indicate notifications."""

    STATES = ("", "success", "info", "warning", "error", "critical")
    COLORS: ty.ClassVar[dict[str, str]] = {
        "info": "#017AFF",
        "critical": "#54100D",
        "error": "#FF0000",
        "warning": "#FF7F00",
        "success": "#00FF00",
    }
    _state = ""

    @property
    def state(self) -> str:
        """Get state."""
        return self._state

    @state.setter
    def state(self, value: ty.Literal["", "success", "info", "warning", "error", "critical"]) -> None:
        if value not in self.STATES:
            raise ValueError(f"Invalid state: {value}. Must be one of {self.STATES}")
        self._state = value

    def paintEvent(self, *args: ty.Any) -> None:
        """Add a notification dot to the label."""
        super().paintEvent(*args)
        if self.state:
            paint = QPainter(self)
            width = self.rect().width() / 6
            radius = self.rect().width() / 8
            x = self.rect().width() - width
            y = self.rect().height() - width
            color = self.COLORS.get(self.state, "#FF0000")
            paint.setPen(QColor(color))
            paint.setBrush(QColor(color))
            paint.drawEllipse(QPointF(x, y), radius, radius)
            paint.end()


class QtQtaTooltipLabel(QtQtaLabel):
    """Label."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self.set_qta("help")
        self.set_qta_size_preset("average")

    def enterEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        """Override to show tooltips instantly."""
        if self.toolTip():
            pos = self.mapToGlobal(self.contentsRect().center())
            QToolTip.showText(pos, self.toolTip(), self)
        super().enterEvent(event)


class QtQtaHelpLabel(QtQtaLabel):
    """Label."""

    _dlg: InfoDialog | None = None

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self.set_qta("help")
        self.set_qta_size_preset("average")

    def enterEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        """Override to show tooltips instantly."""
        if self.toolTip() and not self._dlg:
            self._dlg = InfoDialog(self, self.toolTip())
            self._dlg.evt_close.connect(self._removeDialog)
            self._dlg.show_right_of_widget(self)
        super().enterEvent(event)

    def _removeDialog(self) -> None:
        """Remove dialog."""
        if self._dlg:
            self._dlg = None


class QtSeverityLabel(QtQtaLabel):
    """Severity label."""

    STATES = ("debug", "info", "success", "warning", "error", "critical")

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self._severity: str = "info"
        self.severity = "info"
        self.set_qta_size_preset("xsmall")

    @property
    def severity(self) -> str:
        """Get state."""
        return self._severity

    @severity.setter
    def severity(self, severity: str) -> None:
        self._severity = severity
        self.set_qta(severity)


class QtStateLabel(QtQtaLabel):
    """Severity label."""

    STATES = ("wait", "check", "cross", "active", "upgrade")

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self._state: str = "wait"
        self.state = "wait"

    @property
    def state(self) -> str:
        """Get state."""
        return self._state

    @state.setter
    def state(self, state: str) -> None:
        self._state = state
        self.set_qta(state)


class QtWorkerLabel(QtQtaLabel):
    """Severity label."""

    STATES = ("thread", "process", "cli")

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self._state: str = "wait"
        self.state = "wait"

    @property
    def state(self) -> str:
        """Get state."""
        return self._state

    @state.setter
    def state(self, state: str) -> None:
        self._state = state
        self.set_qta(state)


class QtValidLabel(QtQtaLabel):
    """Severity label."""

    STATES = (
        "success_color",
        "warning_color",
    )

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self._state = True
        self.state = True

    @property
    def state(self) -> bool:
        """Get state."""
        return self._state

    @state.setter
    def state(self, state: bool) -> None:
        self._state = state
        self.set_qta(self.STATES[0] if state else self.STATES[1])

    def enterEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        """Override to show tooltips instantly."""
        if self.toolTip():
            pos = self.mapToGlobal(self.contentsRect().center())
            QToolTip.showText(pos, self.toolTip(), self)
        super().enterEvent(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QHBoxLayout

    from qtextra.assets import QTA_MAPPING, get_icon
    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)

    lay = QHBoxLayout()
    for i, name in enumerate(QTA_MAPPING.keys()):
        icon, qta_kws = get_icon(name)
        qta_kws["scale_factor"] = 1
        label = QtQtaLabel()
        label.set_qta(icon, **qta_kws)
        label.setToolTip(f"{name} :: {icon}")
        label.set_qta_size_preset("large")
        lay.addWidget(label)
        if i % 20 == 0:
            ha.addLayout(lay)
            lay = QHBoxLayout()

    # severity labels
    lay = QHBoxLayout()
    ha.addLayout(lay)
    for state in QtSeverityLabel.STATES:
        btn = QtSeverityLabel()
        btn.set_qta_size_preset("large")
        btn.severity = state
        lay.addWidget(btn)

    # state labels
    lay = QHBoxLayout()
    ha.addLayout(lay)
    for state in QtStateLabel.STATES:
        btn = QtStateLabel()
        btn.set_qta_size_preset("large")
        btn.state = state
        lay.addWidget(btn)

    # worker labels
    lay = QHBoxLayout()
    ha.addLayout(lay)
    for state in QtWorkerLabel.STATES:
        btn = QtWorkerLabel()
        btn.set_qta_size_preset("large")
        btn.state = state
        lay.addWidget(btn)

    # state labels
    lay = QHBoxLayout()
    ha.addLayout(lay)
    for state in [True, False]:
        btn = QtValidLabel()
        btn.set_qta_size_preset("large")
        btn.state = state
        lay.addWidget(btn)

    # pulsing icons
    lay = QHBoxLayout()
    ha.addLayout(lay)
    lay.addWidget(QtWarningPulseLabel(interval=1000))
    lay.addWidget(QtWarningPulseLabel(interval=500))
    lay.addWidget(QtWarningPulseLabel(interval=200))

    # Pulsing attention labels — color transitions every 1 s
    for qta_name, theme_color in [
        ("warning", "warning"),
        ("error", "error"),
        ("info", "success"),
    ]:
        label = QtPulsingAttentionLabel(
            qta_name=qta_name,
            color_from_key=theme_color,
            color_to_key="icon",
            interval=1000,
        )
        label.setToolTip(f"Pulsing attention — {qta_name}")
        lay.addWidget(label)

        label = QtPulsingAttentionLabel(
            qta_name=qta_name,
            color_from_key=theme_color,
            color_to_key="icon",
            interval=500,
        )
        label.setToolTip(f"Pulsing attention — {qta_name}")
        lay.addWidget(label)

    # error labels
    lay = QHBoxLayout()
    ha.addLayout(lay)
    for state in QtQtaNotificationLabel.STATES:
        btn = QtQtaNotificationLabel(state)
        btn.set_large()
        lay.addWidget(btn)
        btn.state = state

    frame.show()
    frame.setMaximumHeight(400)
    sys.exit(app.exec_())
