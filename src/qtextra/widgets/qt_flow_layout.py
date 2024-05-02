"""Qt flow layout."""

from __future__ import annotations

from qtpy.QtCore import QPoint, QRect, QSize, Qt
from qtpy.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget


class QtFlowLayout(QLayout):
    """Implementation of flow layout where widgets are automatically moved around."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = -1):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

        self.items: list[QLayoutItem] = []

    def __del__(self) -> None:
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:
        """Add item to the list."""
        self.items.append(item)

    def count(self) -> int:
        """Get count."""
        return len(self.items)

    # noinspection PyPep8Naming
    def insertWidget(self, index: int, widget: QWidget) -> None:
        """Insert widget at specified position."""
        if index < 0:
            index = self.count()
        self.addWidget(widget)
        item = self.items.pop(len(self.items) - 1)
        self.items.insert(index, item)
        self.invalidate()

    def itemAt(self, index: int) -> QLayoutItem | None:
        """Get item at index."""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        """Take item from index."""
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        """Get expanding direction."""
        return Qt.Orientation(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        """Check height for width."""
        return True

    def heightForWidth(self, width: int) -> int:
        """Get height for width."""
        height = self.update_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect: QRect) -> None:
        """Set geometry."""
        super().setGeometry(rect)
        self.update_layout(rect, False)

    def sizeHint(self) -> QSize:
        """Size hint."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """Minimum size."""
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(int(1.2 * margin), int(1.2 * margin))
        return size

    def update_layout(self, rect: QRect, check_only: bool) -> int:
        """Update layout."""
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self.items:
            wid = item.widget()
            x_spacing = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal
            )
            y_spacing = self.spacing() + wid.style().layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical
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
        return int(y + line_height - rect.y())


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication, QPushButton, QWidget

    class _Window(QWidget):
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
    main_win = _Window()
    main_win.show()
    sys.exit(app.exec_())
