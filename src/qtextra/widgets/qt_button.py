"""Standard Qt button."""
import sys

from qtpy.QtCore import Qt
from qtpy.QtGui import QMovie, QPainter
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy


class QtPushButton(QPushButton):
    """Standard Qt button. Here to enable easier styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QtActivePushButton(QtPushButton):
    """Qt button with activity indicator built-in."""

    _pixmap = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from qtextra.helpers import make_gif

        self.loading_movie = make_gif("square")
        self.loading_movie.frameChanged.connect(self._update_icon)
        self.active = False

    def _update_icon(self, _frame: int):
        """Update frame."""
        self.setIcon(self.loading_movie.currentPixmap())

    @property
    def active(self) -> bool:
        """Update state of the loading label."""
        return self.loading_movie.state() == QMovie.Running

    @active.setter
    def active(self, value: bool):
        self.loading_movie.start() if value else self.loading_movie.stop()
        if not value:
            self.setIcon(None)

    def setIcon(self, icon):
        """Set icon."""
        self._pixmap = icon
        self.repaint()

    def paintEvent(self, event):
        """Paint event/."""
        super().paintEvent(event)
        if self._pixmap is not None:
            y = (self.height() - self._pixmap.height()) / 2
            painter = QPainter(self)
            painter.drawPixmap(5, y, self._pixmap)


class QtRichTextButton(QtPushButton):
    """Rich-text button."""

    def __init__(self, parent=None, text=None):
        super().__init__(parent)
        self._label = QLabel(self)
        if text is not None:
            self._label.setText(text)

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setLayout(self._layout)
        self._label.setAttribute(Qt.WA_TranslucentBackground)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._label.setTextFormat(Qt.RichText)
        self._label.setWordWrap(True)
        self._layout.addWidget(self._label)
        return

    def setText(self, text):
        """Set text on the label."""
        self._label.setText(text)
        self.updateGeometry()

    def sizeHint(self):
        """Return size hints."""
        sh = super().sizeHint()
        lb_sh = self._label.sizeHint()
        sh.setWidth(lb_sh.width() + 15)
        sh.setHeight(lb_sh.height() + 15)
        return sh


if __name__ == "__main__":  # pragma: no cover
    from qtextra.utilities import qframe

    def _test():
        btn1.active = not btn1.active

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)
    btn1 = QtActivePushButton(frame)
    btn1.clicked.connect(_test)
    btn1.setText("TEST BUTTON")
    ha.addWidget(btn1)

    frame.show()
    sys.exit(app.exec_())
