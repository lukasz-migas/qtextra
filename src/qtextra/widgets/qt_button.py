"""Standard Qt button."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import QPointF, Qt, Signal
from qtpy.QtGui import QColor, QMovie, QPainter
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from qtextra.config import THEMES


class QtPushButton(QPushButton):
    """Standard Qt button. Here to enable easier styling."""

    evt_right_click = Signal()
    has_right_click: bool = False

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, evt: QEvent) -> None:  # type: ignore[override]
        """Mouse press event."""
        if evt.button() == Qt.MouseButton.RightButton:  # type: ignore[attr-defined]
            self.evt_right_click.emit()
        else:
            super().mousePressEvent(evt)  # type: ignore[arg-type]

    def paintEvent(self, event) -> None:
        """Paint event/."""
        super().paintEvent(event)
        painter = QPainter(self)
        if self.has_right_click:
            width = 6
            radius = 6
            x = self.rect().width() - (width * 2.0)
            y = self.rect().height() - (width * 2.0)
            color = THEMES.get_hex_color("success")
            painter.setPen(QColor(color))
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPointF(x, y), radius, radius)

    def connect_to_right_click(self, func: ty.Callable) -> None:
        """Connect function right right-click.

        It is not possible to check whether a function is connected to a signal so its better to use this function to
        connect via this function which leaves behind a flag so the paint event will add rectangle to the edge so the
        user knows there is a right-click menu available.
        """
        from qtextra.helpers import set_properties

        self.evt_right_click.connect(func)
        self.has_right_click = True
        set_properties(self, {"right_click": True})


class QtActivePushButton(QtPushButton):
    """Qt button with activity indicator built-in."""

    _pixmap = None

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        from qtextra.helpers import make_gif

        self.loading_movie = make_gif("infinity")
        self.loading_movie.frameChanged.connect(self._update_icon)
        self.active = False

    def _update_icon(self, _frame: int) -> None:
        """Update frame."""
        self.setIcon(self.loading_movie.currentPixmap())

    @property
    def active(self) -> bool:
        """Update the state of the loading label."""
        return self.loading_movie.state() == QMovie.MovieState.Running  # type: ignore[no-any-return]

    @active.setter
    def active(self, value: bool) -> None:
        self.loading_movie.start() if value else self.loading_movie.stop()
        if not value:
            self.setIcon(None)

    def setIcon(self, icon):
        """Set icon."""
        self._pixmap = icon
        self.repaint()

    def paintEvent(self, event) -> None:
        """Paint event/."""
        super().paintEvent(event)
        painter = QPainter(self)
        if self._pixmap is not None:
            y = int((self.height() - self._pixmap.height()) / 2)
            painter.drawPixmap(5, y, self._pixmap)


class QtRichTextButton(QtPushButton):
    """Rich-text button."""

    def __init__(self, parent: QWidget | None = None, text: str | None = None):
        super().__init__(parent)
        self._label = QLabel(self)
        if text is not None:
            self._label.setText(text)

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setLayout(self._layout)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setWordWrap(True)
        self._layout.addWidget(self._label)

    def setText(self, text):
        """Set text on the label."""
        self._label.setText(text)
        self.updateGeometry()

    def text(self):
        """Return text."""
        return self._label.text()

    def sizeHint(self):
        """Return size hints."""
        sh = super().sizeHint()
        lb_sh = self._label.sizeHint()
        sh.setWidth(lb_sh.width() + 15)
        sh.setHeight(lb_sh.height() + 15)
        return sh


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    def _test():
        btn1.active = not btn1.active

    def _test2():
        print("clicked")

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)

    btn1 = QtPushButton(frame)
    btn1.clicked.connect(_test2)
    btn1.connect_to_right_click(_test2)
    btn1.setText("TEST BUTTON")
    ha.addWidget(btn1)

    btn1 = QtActivePushButton(frame)
    btn1.clicked.connect(_test)
    btn1.setText("TEST BUTTON")
    ha.addWidget(btn1)

    btn1 = QtRichTextButton(frame)
    btn1.clicked.connect(_test)
    btn1.setText("TEST <b>button</b>")
    ha.addWidget(btn1)

    frame.show()
    sys.exit(app.exec_())
