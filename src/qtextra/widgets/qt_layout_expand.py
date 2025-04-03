"""Expanding layout."""

from qtpy.QtCore import QEvent, QPoint, QRect, QSize, Qt
from qtpy.QtGui import QResizeEvent
from qtpy.QtWidgets import QLayout, QWidget


class QtExpandLayout(QLayout):
    """Expand layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__items = []
        self.__widgets = []

    def addWidget(self, widget: QWidget):
        if widget in self.__widgets:
            return

        self.__widgets.append(widget)
        widget.installEventFilter(self)

    def addItem(self, item):
        self.__items.append(item)

    def count(self):
        return len(self.__items)

    def itemAt(self, index):
        if 0 <= index < len(self.__items):
            return self.__items[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self.__items):
            self.__widgets.pop(index)
            return self.__items.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Vertical

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        """Get the minimal height according to width."""
        return self.__doLayout(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.__doLayout(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for w in self.__widgets:
            size = size.expandedTo(w.minimumSize())

        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())

        return size

    def __doLayout(self, rect, move):
        """Adjust widgets position according to the window size."""
        margin = self.contentsMargins()
        x = rect.x() + margin.left()
        y = rect.y() + margin.top()
        width = rect.width() - margin.left() - margin.right()

        for i, w in enumerate(self.__widgets):
            if w.isHidden():
                continue

            y += (i > 0) * self.spacing()
            if move:
                w.setGeometry(QRect(QPoint(x, y), QSize(width, w.height())))

            y += w.height()

        return y - rect.y()

    def eventFilter(self, obj, e):
        if obj in self.__widgets:
            if e.type() == QEvent.Type.Resize:
                re = QResizeEvent(e)
                ds = re.size() - re.oldSize()  # type:QSize
                if ds.height() != 0 and ds.width() == 0:
                    w = self.parentWidget()
                    w.resize(w.width(), w.height() + ds.height())

        return super().eventFilter(obj, e)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QPushButton

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(with_layout=False)
    frame.setMinimumSize(600, 600)
    flow_layout = QtExpandLayout()
    for text in [
        "Short",
        "Longer",
        "Different text",
        "More text",
        "Even longer button text",
        "Short",
        "Longer",
        "Different text",
        "More text",
        "Even longer button text",
    ]:
        flow_layout.addWidget(QPushButton(text))
    frame.setLayout(flow_layout)

    frame.show()
    sys.exit(app.exec_())
