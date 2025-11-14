"""QtIcon."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from koyo.typing import PathLike
from qtpy.QtCore import QSize, Qt, Signal  # type: ignore[attr-defined]  # type: ignore[attr-defined]
from qtpy.QtGui import QEnterEvent, QPixmap, QResizeEvent
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


class QtQtaTooltipLabel(QtQtaLabel):
    """Label."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self.set_qta("help")
        self.set_average()

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
        self.set_average()

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
        self.set_xsmall()

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


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QHBoxLayout

    from qtextra.assets import QTA_MAPPING, get_icon
    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)

    lay = QHBoxLayout()
    for i, name in enumerate(QTA_MAPPING.keys()):
        qta_name, qta_kws = get_icon(name)
        qta_kws["scale_factor"] = 1
        label = QtQtaLabel()
        label.set_qta(qta_name, **qta_kws)
        label.setToolTip(f"{name} :: {qta_name}")
        label.set_large()
        lay.addWidget(label)
        if i % 20 == 0:
            ha.addLayout(lay)
            lay = QHBoxLayout()
    # add labels
    lay = QHBoxLayout()
    ha.addLayout(lay)
    for state in QtSeverityLabel.STATES:
        btn = QtSeverityLabel()
        btn.set_large()
        btn.severity = state
        lay.addWidget(btn)
    lay = QHBoxLayout()
    ha.addLayout(lay)
    for state in QtStateLabel.STATES:
        btn = QtStateLabel()
        btn.set_large()
        btn.state = state
        lay.addWidget(btn)

    for state in QtWorkerLabel.STATES:
        btn = QtWorkerLabel()
        btn.set_large()
        btn.state = state
        lay.addWidget(btn)

    frame.show()
    frame.setMaximumHeight(400)
    sys.exit(app.exec_())
