"""
Adapted from:
https://wiki.python.org/moin/PyQt/A%20full%20widget%20waiting%20indicator
Also from:
https://github.dev/royerlab/aydin/blob/c19595f37a163f6cd34243c5d5975cddb4a637c1/aydin/gui/_qt/custom_widgets/overlay.py.
"""
from qtpy.QtCore import Qt
from qtpy.QtGui import QBrush, QColor, QPainter, QPalette, QPen
from qtpy.QtWidgets import QVBoxLayout, QWidget


class QtActiveOverlay(QWidget):
    """Widget that displays that action is in progress."""

    timer = None
    counter: int = 0
    reverse: bool = False
    n_dots: int = 5
    interval: int = 200

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)

        self.BLUE = QColor(0, 191, 255)
        self.GRAY = QColor(197, 197, 197)

        self.setPalette(palette)

    def paintEvent(self, event):
        """Paint event."""
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(event.rect(), QBrush(QColor(40, 45, 60, 197)))
        painter.setPen(QPen(Qt.NoPen))

        for i in range(self.n_dots):
            if i <= self.counter:
                painter.setBrush(QBrush(self.BLUE if not self.reverse else self.GRAY))
            else:
                painter.setBrush(QBrush(self.GRAY if not self.reverse else self.BLUE))
            painter.drawEllipse(self.width() // 2 + 50 * i - 100, self.height() // 2, 20, 20)
        painter.end()

    def showEvent(self, event):
        """Show event."""
        self.timer = self.startTimer(self.interval)
        self.counter = 0

    def timerEvent(self, event):
        """Timer event."""
        self.counter += 1
        if self.counter >= self.n_dots:
            self.reverse = not self.reverse
            self.counter = 0
        self.update()

    def hideEvent(self, event):
        """Hide event."""
        self.killTimer(self.timer)
        self.hide()


class QtActiveWidget(QWidget):
    """Widget that displays activity."""

    def __init__(self, msg: str = "", size=(64, 64), parent=None):
        super().__init__(parent)

        from qtextra.helpers import make_label, make_loading_gif

        label = make_label(self, msg, bold=True)
        spinner, _ = make_loading_gif(self, size=size)

        layout = QVBoxLayout(self)
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(spinner, alignment=Qt.AlignmentFlag.AlignCenter)
