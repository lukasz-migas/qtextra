import typing as ty

from qtpy import QtCore, QtGui
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, Signal


class QtClickLabel(QtW.QLabel):
    """Clickable label without highlight."""

    evt_clicked = Signal()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        """Emit the clicked signal when the left mouse button is released."""
        if ev.button() == Qt.MouseButton.LeftButton:
            self.evt_clicked.emit()
        return super().mouseReleaseEvent(ev)


class QtVerticalLabel(QtW.QLabel):
    """Rotated label."""

    def __init__(self, *args):
        QtW.QLabel.__init__(self, *args)

    def paintEvent(self, event) -> None:
        painter = QtGui.QPainter(self)
        painter.translate(0, self.height())
        painter.rotate(-90)
        # calculate the size of the font
        fm = QtGui.QFontMetrics(painter.font())
        xoffset = int(fm.boundingRect(self.text()).width() / 2)
        yoffset = int(fm.boundingRect(self.text()).height() / 2)
        x = int(self.width() / 2) + yoffset
        y = int(self.height() / 2) - xoffset
        # because we rotated the label, x affects the vertical placement, and y affects the horizontal
        painter.drawText(y, x, self.text())

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        return QtCore.QSize(size.height(), size.width())

    def sizeHint(self):
        size = super().sizeHint()
        return QtCore.QSize(size.height(), size.width())


class QtClickableLabel(QtW.QLabel):
    """A label widget that behaves like a button."""

    evt_clicked = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = ""
        self._elide_mode = Qt.TextElideMode.ElideNone
        # self.setFixedHeight(24)

        self.setSizePolicy(QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setText(text)

    def elideMode(self) -> Qt.TextElideMode:
        """The current Qt.TextElideMode."""
        return self._elide_mode

    def setElideMode(self, mode: Qt.TextElideMode) -> None:
        """Set the elide mode to a Qt.TextElideMode."""
        self._elide_mode = Qt.TextElideMode(mode)
        super().setText(self._elidedText())

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        """Emit the clicked signal when the left mouse button is released."""
        if ev.button() == Qt.MouseButton.LeftButton:
            self.evt_clicked.emit()
        return super().mouseReleaseEvent(ev)

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        """Add an underline to the text and change the cursor to a hand."""
        font = self.font()
        font.setUnderline(True)
        self.setFont(font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        """Reset the text and cursor to their original state."""
        font = self.font()
        font.setUnderline(False)
        self.setFont(font)
        self.unsetCursor()
        return super().leaveEvent(a0)

    # Reimplemented QT methods

    def text(self) -> str:
        """Return the label's text.

        If no text has been set this will return an empty string.
        """
        return self._text

    def setText(self, text: str):
        """Set the label's text.

        Setting the text clears any previous content.
        NOTE: we set the QLabel private text to the elided version
        """
        self._text = text
        super().setText(self._elidedText())

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        """Resize event."""
        ev.accept()
        super().setText(self._elidedText())

    def _elidedText(self) -> str:
        """Return `self._text` elided to `width`."""
        fm = QtGui.QFontMetrics(self.font())
        # the 2 is a magic number that prevents the ellipses from going missing
        # in certain cases (?)
        width = self.width() - 2
        if not self.wordWrap():
            return fm.elidedText(self._text, self._elide_mode, width)

        # get number of lines we can fit without eliding
        nlines = self.height() // fm.height() - 1
        # get the last line (elided)
        text = self._wrappedText()
        last_line = fm.elidedText("".join(text[nlines:]), self._elide_mode, width)
        # join them
        return "".join(text[:nlines] + [last_line])

    def _wrappedText(self) -> ty.List[str]:
        return QtClickableLabel.wrapText(self._text, self.width(), self.font())


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    def _test():
        print("clicked")

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)
    widget = QtClickableLabel("Test that will be underlined when hovered over", frame)
    widget.evt_clicked.connect(_test)
    ha.addWidget(widget, stretch=True)

    frame.show()
    sys.exit(app.exec_())
