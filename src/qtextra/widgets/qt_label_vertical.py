"""Vertical label."""

from qtpy import QtCore, QtGui
from qtpy import QtWidgets as QtW


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


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    def _test():
        print("clicked")

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)
    ha.addWidget(QtVerticalLabel("Test 1 with more text"), stretch=True)

    frame.show()
    sys.exit(app.exec_())
