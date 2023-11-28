"""QtIcon."""
import typing as ty

from qtpy.QtCore import QSize, Qt, Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QLabel

from qtextra.config import THEMES
from qtextra.widgets._qta_mixin import QtaMixin


class QtActiveIcon(QLabel):
    """Active icon that shows activity."""

    def __init__(self, which: str = "square", size: tuple[int, int] = (20, 20), start: bool = False):
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


class QtIconLabel(QLabel):
    """Label with icon."""

    evt_clicked = Signal()

    def __init__(self, object_name: str, *args, **kwargs):
        super().__init__()
        self.setMouseTracking(True)
        self.setObjectName(object_name)

    def mousePressEvent(self, ev):
        """Mouse press event."""
        if ev.button() == Qt.LeftButton:
            self.evt_clicked.emit()
        super().mousePressEvent(ev)


class QtQtaLabel(QtIconLabel, QtaMixin):
    """Label."""

    _icon = None

    def __init__(
        self, *args, small: bool = False, large: bool = False, xlarge: bool = False, xxlarge: bool = False, **kwargs
    ):
        super().__init__("", *args, **kwargs)
        self._size = QSize(28, 28)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        self.set_default_size(small, large, xlarge, xxlarge)
        THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def setIcon(self, _icon) -> None:
        """Update icon."""
        self._icon = _icon
        self.setPixmap(_icon.pixmap(self._size))

    def setIconSize(self, size):
        """
        set icon size.

        Parameters
        ----------
        size: QtCore.QSize
            size of the icon
        """
        self._size = size
        self.update()

    def update(self, *args, **kwargs):
        """Update label."""
        if self._icon:
            self.setPixmap(self._icon.pixmap(self._size))
        return super().update(*args, **kwargs)


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
    def severity(self, severity: str):
        self._severity = severity
        self.set_qta(severity)


class QtStateLabel(QtQtaLabel):
    """Severity label."""

    STATES = ("wait", "check", "cross", "active", "upgrade", "thread", "process", "cli")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state: str = "wait"
        self.state = "wait"

    @property
    def state(self) -> str:
        """Get state."""
        return self._state

    @state.setter
    def state(self, state: str):
        self._state = state
        self.set_qta(state)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QVBoxLayout

    from qtextra.assets import QTA_MAPPING
    from qtextra.utils.dev import qframe

    app, frame, ha = qframe()

    lay = QVBoxLayout()
    for i, (name, qta_name) in enumerate(QTA_MAPPING.items()):
        label = QtQtaLabel()
        label.set_qta(qta_name, scale_factor=1)
        label.setToolTip(f"{name} :: {qta_name}")
        label.set_large()
        lay.addWidget(label)
        if i % 10 == 0:
            ha.addLayout(lay)
            lay = QVBoxLayout()

    frame.show()
    frame.setMaximumHeight(400)
    sys.exit(app.exec_())
