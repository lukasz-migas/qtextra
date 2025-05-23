"""
Adapted from:
https://wiki.python.org/moin/PyQt/A%20full%20widget%20waiting%20indicator
Also from:
https://github.dev/royerlab/aydin/blob/c19595f37a163f6cd34243c5d5975cddb4a637c1/aydin/gui/_qt/custom_widgets/overlay.py.
"""

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QBrush, QPainter, QPen
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES

# TODO: it's possible that QtActiveOverlay is not always centered


class QtActiveOverlay(QWidget):
    """Widget that displays that action is in progress."""

    timer = None
    counter: int = 0

    # Attributes
    REVERSE: bool = False
    N_DOTS: int = 5
    INTERVAL: int = 200
    SIZE = 20
    SPACING = 50

    def __init__(self, n_dots: int = 5, interval: int = 200, size: int = 20, spacing=50, parent=None):
        self.N_DOTS = n_dots
        self.INTERVAL = interval
        self.SIZE = size
        self.SPACING = spacing
        QWidget.__init__(self, parent)

    def paintEvent(self, event):
        """Paint event."""
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background
        painter.fillRect(event.rect(), QBrush(THEMES.get_qt_color("background")))

        # No border
        painter.setPen(QPen(Qt.PenStyle.NoPen))

        # Vertical position for the dots
        height = (self.height() - self.SIZE) // 2

        # Calculate total width of all dots with spacing
        total_width = (self.N_DOTS - 1) * self.SPACING + self.SIZE

        # Calculate left margin to center the dots horizontally
        horizontal_offset = (self.width() - total_width) // 2

        # Draw each dot
        for i in range(self.N_DOTS):
            if i <= self.counter:
                color = "success" if not self.REVERSE else "primary"
            else:
                color = "primary" if not self.REVERSE else "success"
            painter.setBrush(QBrush(THEMES.get_qt_color(color)))
            x = horizontal_offset + i * self.SPACING
            painter.drawEllipse(x, height, self.SIZE, self.SIZE)

    def showEvent(self, event):
        """Show event."""
        self.timer = self.startTimer(self.INTERVAL)
        self.counter = 0

    def timerEvent(self, event):
        """Timer event."""
        self.counter += 1
        if self.counter >= self.N_DOTS:
            self.REVERSE = not self.REVERSE
            self.counter = 0
        self.update()

    def hideEvent(self, event):
        """Hide event."""
        self.killTimer(self.timer)
        self.hide()

    def sizeHint(self) -> QSize:
        """Return the size hint for the widget."""
        return QSize(self.SPACING * (self.N_DOTS + 1), 120)

    def minimumHeight(self) -> QSize:
        """Return the minimum height for the widget."""
        return QSize(self.SPACING * (self.N_DOTS + 1), 120)


class QtActiveWidget(QWidget):
    """Widget that displays activity."""

    def __init__(self, text: str = "", which: str = "infinity", size: tuple[int, int] = (64, 64), parent=None):
        super().__init__(parent)

        from qtextra.helpers import make_label, make_loading_gif

        label = make_label(self, text, bold=True)
        spinner, _ = make_loading_gif(self, size=size, which=which)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(spinner, alignment=Qt.AlignmentFlag.AlignCenter)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, va = qframe(False)

        va.addWidget(QLabel("QtActiveWidget"), alignment=Qt.AlignmentFlag.AlignHCenter)
        va.addWidget(QtActiveWidget(parent=frame))
        va.addWidget(QLabel("QtActiveOverlay"), alignment=Qt.AlignmentFlag.AlignHCenter)
        va.addWidget(QtActiveOverlay(parent=frame))

        frame.show()
        sys.exit(app.exec_())

    _main()
