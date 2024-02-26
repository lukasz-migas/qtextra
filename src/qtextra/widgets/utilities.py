from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QLabel, QStyle, QStyleOption, QVBoxLayout, QWidget

import qtextra.helpers as hp


def get_text_color(background: QColor, light_color: QColor = None, dark_color: QColor = None):
    """Select color depending on whether the background is light or dark.

    Parameters
    ----------
    background : QColor
        background color
    light_color : QColor
        the color used on light background
    dark_color : QColor
        the color used on dark background
    """
    if light_color is None:
        light_color = QColor("#000000")
    if dark_color is None:
        dark_color = QColor("#FFFFFF")
    is_dark = is_dark_color(background)
    return dark_color if is_dark else light_color


def is_dark_color(background: QColor):
    """Check whether its a dark background."""
    a = 1 - (0.299 * background.redF() + 0.587 * background.greenF() + 0.114 * background.blueF())
    return background.alphaF() > 0 and a >= 0.3


class QtLargeLabel(QLabel):
    """Large label."""


class QtWelcomeLabel(QLabel):
    """Labels used for main message in welcome page."""


class QtShortcut(QLabel):
    """Labels used for displaying shortcut information in welcome page."""


class QtShortcutLabel(QLabel):
    """Labels used for displaying shortcut information in welcome page."""


class QtDragWidget(QWidget):
    """Drag widget."""

    evt_dropped = Signal("QEvent")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAutoFillBackground(True)
        self.setAcceptDrops(True)

    def _update_property(self, prop, value):
        """Update properties of widget to update style.

        Parameters
        ----------
        prop : str
            Property name to update.
        value : bool
            Property value to update.
        """
        self.setProperty(prop, value)
        hp.polish_widget(self)

    def dragEnterEvent(self, event):
        """Override Qt method.

        Provide style updates on event.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._update_property("drag", True)
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Override Qt method.

        Provide style updates on event.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._update_property("drag", False)

    def dropEvent(self, event):
        """Override Qt method.

        Provide style updates on event and emit the drop event.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._update_property("drag", False)
        self.evt_dropped.emit(event)

    def paintEvent(self, event):
        """Override Qt method.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        option = QStyleOption()
        option.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, p, self)


class MessageWidget(QWidget):
    """Widget that displays a message at the center of the page."""

    def __init__(self, message: str, parent=None, icon: str = ""):
        super().__init__(parent)

        self.icon = hp.make_qta_label(self, icon)
        self.icon.setVisible(icon != "")

        self.label = QtWelcomeLabel(message)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addStretch(True)
        layout.addWidget(self.icon)
        layout.addWidget(self.label)
        layout.addStretch(True)

    @property
    def message(self) -> str:
        """Return current message."""
        return self.label.text()

    @message.setter
    def message(self, value: str):
        self.label.setText(value)
