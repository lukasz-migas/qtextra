"""Qt flow layout."""
from qtpy.QtCore import QPoint, QRect, QSize, Qt
from qtpy.QtWidgets import QLayout, QSizePolicy


class QtFlowLayout(QLayout):
    """Implementation of flow layout where widgets are automatically moved around."""

    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

        self.items = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        """Add item to the list."""
        self.items.append(item)

    def count(self) -> int:
        """Get count."""
        return len(self.items)

    # noinspection PyPep8Naming
    def insertWidget(self, index: int, widget):
        """Insert widget at specified position."""
        if index < 0:
            index = self.count()
        self.addWidget(widget)
        item = self.items.pop(len(self.items) - 1)
        self.items.insert(index, item)
        self.invalidate()

    def itemAt(self, index: int):
        """Get item at index."""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def takeAt(self, index: int):
        """Take item from index."""
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def expandingDirections(self):
        """Get expanding direction."""
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        """Check height for width."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Get height for width."""
        height = self.update_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        """Set geometry."""
        super().setGeometry(rect)
        self.update_layout(rect, False)

    def sizeHint(self):
        """Size hint."""
        return self.minimumSize()

    def minimumSize(self):
        """Minimum size."""
        size = QSize()

        for item in self.items:
            size = size.expandedTo(item.minimumSize())

        margin, _, _, _ = self.getContentsMargins()

        size += QSize(2 * margin, 2 * margin)
        return size

    def update_layout(self, rect, check_only: bool):
        """Update layout."""
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self.items:
            wid = item.widget()
            x_spacing = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Orientation.Horizontal
            )
            y_spacing = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Orientation.Vertical
            )
            x_next = x + item.sizeHint().width() + x_spacing
            if x_next - x_spacing > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + y_spacing
                x_next = x + item.sizeHint().width() + x_spacing
                line_height = 0

            if not check_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = x_next
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication, QPushButton, QWidget

    class Window(QWidget):
        def __init__(self):
            super().__init__()

            flow_layout = QtFlowLayout(self)
            flow_layout.addWidget(QPushButton("Short"))
            flow_layout.addWidget(QPushButton("Longer"))
            flow_layout.addWidget(QPushButton("Different text"))
            flow_layout.addWidget(QPushButton("More text"))
            flow_layout.addWidget(QPushButton("Even longer button text"))

            self.setWindowTitle("Flow Layout")

    app = QApplication(sys.argv)
    main_win = Window()
    main_win.show()
    sys.exit(app.exec_())
