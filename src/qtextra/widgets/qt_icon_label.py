"""QtIcon."""
import qtawesome
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtWidgets import QLabel

from qtextra.assets import get_icon
from qtextra.config import THEMES


class QtIconLabel(QLabel):
    """Label with icon."""

    evt_clicked = Signal()

    def __init__(self, object_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.setObjectName(object_name)

    def mousePressEvent(self, ev):
        """Mouse press event."""
        if ev.button() == Qt.LeftButton:
            self.evt_clicked.emit()
        super().mousePressEvent(ev)


class QtQtaLabel(QtIconLabel):
    """Label."""

    _icon = None
    _qta_data = None

    def __init__(
        self, *args, small: bool = False, large: bool = False, xlarge: bool = False, xxlarge: bool = False, **kwargs
    ):
        super().__init__("", *args, **kwargs)
        self._size = QSize(28, 28)
        self.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.set_size(small, large, xlarge, xxlarge)
        THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def set_qta(self, name: str, **kwargs):
        """Set QtAwesome icon."""
        name = get_icon(name)
        self._qta_data = (name, kwargs)
        icon = qtawesome.icon(name, **self._qta_data[1], color=THEMES.get_hex_color("icon"))
        self.setIcon(icon)

    def set_size(
        self,
        xsmall: bool = False,
        small: bool = False,
        large: bool = False,
        xlarge: bool = False,
        xxlarge: bool = False,
    ):
        """Set size of the icon."""
        if xsmall:
            self.set_xsmall()
        elif small:
            self.set_small()
        elif large:
            self.set_large()
        elif xlarge:
            self.set_xlarge()
        elif xxlarge:
            self.set_xxlarge()

    def set_xsmall(self):
        """Set large."""
        self.setObjectName("xsmall_icon")
        self.setIconSize(QSize(10, 10))

    def set_small(self):
        """Set large."""
        self.setObjectName("small_icon")
        self.setIconSize(QSize(20, 20))

    def set_large(self):
        """Set large."""
        self.setObjectName("large_icon")
        self.setIconSize(QSize(40, 40))

    def set_xlarge(self):
        """Set large."""
        self.setObjectName("xlarge_icon")
        self.setIconSize(QSize(60, 60))

    def set_xxlarge(self):
        """Set large."""
        self.setObjectName("xxlarge_icon")
        self.setIconSize(QSize(80, 80))

    def set_xxxlarge(self):
        """Set large."""
        self.setObjectName("xxxlarge_icon")
        self.setIconSize(QSize(120, 120))

    def _update_qta(self):
        """Update qta icon."""
        if self._qta_data:
            name, kwargs = self._qta_data
            self.set_qta(name, **kwargs)

    def setIcon(self, _icon):
        """
        set a new icon().

        Parameters
        ----------
        _icon: qtawesome.icon
            icon to set
        """
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._severity: str = "info"
        self.severity = "info"
        self.set_small()

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

    from qtextra.utils.dev import qframe
    from qtextra.assets import QTA_MAPPING

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
