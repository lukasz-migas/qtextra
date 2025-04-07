"""
Adapted from:
https://wiki.python.org/moin/PyQt/A%20full%20widget%20waiting%20indicator
Also from:
https://github.dev/royerlab/aydin/blob/c19595f37a163f6cd34243c5d5975cddb4a637c1/aydin/gui/_qt/custom_widgets/overlay.py.
"""

from qtpy.QtCore import Qt
from qtpy.QtGui import QBrush, QPainter, QPen
from qtpy.QtWidgets import QVBoxLayout, QWidget

from qtextra.config import THEMES


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

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

    def paintEvent(self, event):
        """Paint event."""
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(event.rect(), QBrush(THEMES.get_qt_color("background")))
        painter.setPen(QPen(Qt.PenStyle.NoPen))

        for i in range(self.N_DOTS):
            if i <= self.counter:
                painter.setBrush(QBrush(THEMES.get_qt_color("success" if not self.REVERSE else "primary")))
            else:
                painter.setBrush(QBrush(THEMES.get_qt_color("primary" if not self.REVERSE else "success")))
            painter.drawEllipse(
                self.width() // 2 + self.SPACING * i - (self.SPACING * 2), self.height() // 2, self.SIZE, self.SIZE
            )
        painter.end()

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


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qmain, theme_toggle_btn

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)
        ha.addWidget(theme_toggle_btn(frame))

        wdg = QtActiveWidget(parent=frame)
        ha.addWidget(wdg)
        wdg = QtActiveOverlay(parent=frame)
        ha.addWidget(wdg)

        frame.show()
        sys.exit(app.exec_())

    _main()
