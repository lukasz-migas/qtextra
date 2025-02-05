"""Status bar widgets.

Taken and modified from spyder.widgets.status
"""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import QSize, Qt, QTimer, Signal
from qtpy.QtGui import QFont, QIcon, QMouseEvent
from qtpy.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QStatusBar, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_tool import QtToolButton
from qtextra.widgets.qt_label_icon import QtQtaLabel


class QtStatusbarLabel(QLabel):
    """Statusbar label."""

    def __init__(self, parent: QWidget | None, statusbar: QStatusBar, text: str = "", font_size: int = 7):
        """Status bar progress bar."""
        super().__init__(parent)

        self.setText(text)
        self.setFont(hp.get_font(font_size))

        # Setup
        statusbar.addPermanentWidget(self)


class QtStatusbarToolBtn(QtToolButton):
    """Status bar tool button base."""

    def __init__(self, parent: QWidget | None, statusbar: QStatusBar, text: str = "", icon: QIcon | None = None):
        """Status bar widget base."""
        super().__init__(parent, text=text, icon=icon)
        self.setFont(hp.get_font(7))

        # Widget
        self._status_bar = statusbar
        # Setup
        statusbar.addPermanentWidget(self)


class QtStatusbarProgressbar(QProgressBar):
    """Statusbar progressbar."""

    def __init__(self, parent: QWidget | None, statusbar: QStatusBar):
        """Status bar progress bar."""
        super().__init__(parent)

        # Setup sizing policy
        size_policy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(size_policy)

        self.setFont(hp.get_font(7))

        # Setup
        statusbar.addPermanentWidget(self)


class QtStatusbarSpinner(QWidget):
    """Statusbar spinner."""

    def __init__(self, parent: QWidget | None, statusbar: QStatusBar):
        super().__init__(parent)

        self.spinner, self.movie = hp.make_loading_gif(parent, size=(18, 18))

        layout = QHBoxLayout()
        layout.addWidget(self.spinner)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        statusbar.addPermanentWidget(self)

    def start(self) -> None:
        """Start spinner."""
        self.spinner.show()

    def stop(self) -> None:
        """Stop spinner."""
        self.spinner.hide()


class QtStatusbarIconWidget(QWidget):
    """Status bar widget with single icon."""

    # Signals
    evt_clicked = Signal()

    def __init__(self, parent: QWidget | None, statusbar: QStatusBar, name: str = "", index: ty.Optional[int] = None):
        """Status bar widget base."""
        super().__init__(parent)
        self.setMouseTracking(True)

        # Widget
        self._status_bar = statusbar
        self._icon = None
        self._pixmap = None
        self._icon_size = QSize(16, 16)  # ; should this be adjutable?
        self.label_icon = QtQtaLabel()
        if name:
            self.label_icon.set_qta(name)
            self.label_icon.set_small()

        # Layout setup
        layout = QHBoxLayout(self)
        layout.setSpacing(0)  # Reduce space between icon and label
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label_icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Setup
        if index is None:
            statusbar.addPermanentWidget(self)
        else:
            statusbar.insertPermanentWidget(index, self)
        self.update_tooltip()

    def update_tooltip(self) -> None:
        """Update tooltip for widget."""
        tooltip = self.get_tooltip()
        if tooltip:
            if self.label_icon:
                self.label_icon.setToolTip(tooltip)
            self.setToolTip(tooltip)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Override Qt method to allow for click signal."""
        super().mousePressEvent(event)
        self.evt_clicked.emit()

    def get_tooltip(self) -> str:
        """Return the widget tooltip text."""
        return ""

    def flash(self, duration: int = 500, color: tuple = (0.5, 0.5, 0.5, 0.5)) -> None:
        """Add simple flash animation to highlight an event."""
        hp.add_flash_animation(self, duration, color, 3)


class QtStatusbarWidget(QtStatusbarIconWidget):
    """Status bar widget base."""

    # Signals
    evt_clicked = Signal()

    def __init__(
        self,
        parent: QWidget | None,
        statusbar: QStatusBar,
        name: str = "",
        example_text: str | None = None,
        hide_label: bool = False,
    ):
        """Status bar widget base."""
        super().__init__(parent, statusbar, name=name)
        # Variables
        self.value: str | None = None
        self.label_value = QLabel()

        # Layout setup
        self.layout().addWidget(self.label_value)  # type: ignore[union-attr]

        # See spyder-ide/spyder#9044.
        self.label_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.label_value.setFont(hp.get_font(7, QFont.Weight.Bold))
        if hide_label:
            self.label_value.setVisible(False)

        # Widget setup
        if example_text:
            fm = self.label_value.fontMetrics()
            self.label_value.setMinimumWidth(fm.horizontalAdvance(example_text))
        self.setMinimumWidth(self.label_icon.minimumWidth() + self.label_value.minimumWidth())

        # Setup
        statusbar.addPermanentWidget(self)
        self.set_value("")
        self.update_tooltip()

    def set_value(self, value: str) -> None:
        """Set formatted text value."""
        self.value = value
        self.label_value.setText(value)

    def update_tooltip(self) -> None:
        """Update tooltip for widget."""
        tooltip = self.get_tooltip()
        if tooltip and hasattr(self, "label_value"):
            self.label_value.setToolTip(tooltip)
            if self.label_icon:
                self.label_icon.setToolTip(tooltip)
            self.setToolTip(tooltip)


class QtStatusbarTimerBase(QtStatusbarWidget):
    """Status bar widget base for widgets that update based on timers."""

    def __init__(self, parent: QWidget | None, statusbar: QStatusBar, name: str = "", example_text: str | None = None):
        """Status bar widget base for widgets that update based on timers."""
        self.timer = None  # Needs to come before parent call
        super().__init__(parent, statusbar, name=name, example_text=example_text)
        self._interval = 2000

        # Setup
        if self.is_supported():
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_status)
            self.timer.start(self._interval)
        else:
            self.hide()

    def setVisible(self, value: bool) -> None:
        """Override Qt method to stops timers if widget is not visible."""
        if self.timer is not None:
            if value:
                self.timer.start(self._interval)
            else:
                self.timer.stop()
        super().setVisible(value)

    def is_supported(self) -> bool:
        """Return True if feature is supported."""
        try:
            self.import_test()
            return True
        except ImportError:
            return False

    def update_status(self) -> None:
        """Update status label widget, if widget is visible."""
        if self.isVisible():
            self.label_value.setText(self.get_value())

    def set_interval(self, interval: int) -> None:
        """Set timer interval (ms)."""
        self._interval = interval
        if self.timer is not None:
            self.timer.setInterval(interval)

    def import_test(self) -> None:
        """Raise ImportError if feature is not supported."""
        raise NotImplementedError

    def get_value(self) -> str:
        """Return formatted text value."""
        raise NotImplementedError


class QtStatusbarMemory(QtStatusbarTimerBase):
    """Status bar widget for system memory usage."""

    def import_test(self) -> None:
        """Raise ImportError if feature is not supported."""
        from qtextra.utils.utilities import memory_usage

        del memory_usage

    def get_value(self) -> str:
        """Return memory usage."""
        from qtextra.utils.utilities import memory_usage

        text = "%d%%" % memory_usage()
        return "Mem " + text.rjust(3) if not self._pixmap else " " + text.rjust(3)

    def get_tooltip(self) -> str:
        """Return the widget tooltip text."""
        return "Memory usage"


class QtStatusbarProcessMemory(QtStatusbarTimerBase):
    """Status bar widget for system memory usage."""

    def import_test(self) -> None:
        """Raise ImportError if feature is not supported."""
        from qtextra.utils.utilities import process_memory_usage

        del process_memory_usage

    def get_value(self) -> str:
        """Return memory usage."""
        from qtextra.utils.utilities import process_memory_usage

        try:
            text = "%d%%" % process_memory_usage()
        except Exception:
            text = "N/A"
        return "Mem " + text.rjust(3) if not self._pixmap else " " + text.rjust(3)

    def get_tooltip(self) -> str:
        """Return the widget tooltip text."""
        return "Memory usage"


class QtStatusbarCPU(QtStatusbarTimerBase):
    """Status bar widget for system cpu usage."""

    def import_test(self) -> None:
        """Raise ImportError if feature is not supported."""

    def get_value(self) -> str:
        """Return CPU usage."""
        import psutil

        text = "%d%%" % psutil.cpu_percent(interval=0)
        return "CPU " + text.rjust(3) if not self._pixmap else " " + text.rjust(3)

    def get_tooltip(self) -> str:
        """Return the widget tooltip text."""
        return "CPU usage"


class QtStatusbarProcessCPU(QtStatusbarTimerBase):
    """Status bar widget for system cpu usage."""

    def import_test(self) -> None:
        """Raise ImportError if feature is not supported."""

    def get_value(self) -> str:
        """Return CPU usage."""
        import psutil

        try:
            text = "%d%%" % psutil.Process().cpu_percent(interval=0)
        except Exception:
            text = "N/A"
        return "CPU " + text.rjust(3) if not self._pixmap else " " + text.rjust(3)

    def get_tooltip(self) -> str:
        """Return the widget tooltip text."""
        return "CPU usage"
