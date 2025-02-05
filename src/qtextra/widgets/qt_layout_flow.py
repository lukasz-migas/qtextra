"""Qt flow layout."""

from __future__ import annotations

from typing import List

from qtpy.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
)
from qtpy.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget, QWidgetItem


class QtAnimatedFlowLayout(QLayout):
    """Flow layout."""

    def __init__(self, parent=None, use_animation=False, tight=False):
        """
        Parameters
        ----------
        parent:
            parent window or layout

        use_animation: bool
            whether to add moving animation

        tight: bool
            whether to use the tight layout when widgets are hidden
        """
        super().__init__(parent)
        self._items = []  # type: List[QLayoutItem]
        self._anis = []  # type: List[QPropertyAnimation]
        self._aniGroup = QParallelAnimationGroup(self)
        self._verticalSpacing = 10
        self._horizontalSpacing = 10
        self.duration = 300
        self.ease = QEasingCurve.Linear
        self.use_animation = use_animation
        self.tight = tight
        self._deBounceTimer = QTimer(self)
        self._deBounceTimer.setSingleShot(True)
        self._deBounceTimer.timeout.connect(lambda: self._doLayout(self.geometry(), True))
        self._wParent = None
        self._isInstalledEventFilter = False

    def addItem(self, item):
        self._items.append(item)

    def insertItem(self, index, item):
        self._items.insert(index, item)

    def addWidget(self, w):
        super().addWidget(w)
        self._onWidgetAdded(w)

    def insertWidget(self, index, w):
        self.insertItem(index, QWidgetItem(w))
        self.addChildWidget(w)
        self._onWidgetAdded(w, index)

    def _onWidgetAdded(self, w, index=-1):
        if not self._isInstalledEventFilter:
            if w.parent():
                self._wParent = w.parent()
                w.parent().installEventFilter(self)
            else:
                w.installEventFilter(self)

        if not self.use_animation:
            return

        ani = QPropertyAnimation(w, b"geometry")
        ani.setEndValue(QRect(QPoint(0, 0), w.size()))
        ani.setDuration(self.duration)
        ani.setEasingCurve(self.ease)
        w.setProperty("flowAni", ani)
        self._aniGroup.addAnimation(ani)

        if index == -1:
            self._anis.append(ani)
        else:
            self._anis.insert(index, ani)

    def setAnimation(self, duration, ease=QEasingCurve.Linear):
        """Set the moving animation.

        Parameters
        ----------
        duration: int
            the duration of animation in milliseconds

        ease: QEasingCurve
            the easing curve of animation
        """
        if not self.use_animation:
            return

        self.duration = duration
        self.ease = ease

        for ani in self._anis:
            ani.setDuration(duration)
            ani.setEasingCurve(ease)

    def count(self):
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]

        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            item = self._items[index]  # type: QLayoutItem
            ani = item.widget().property("flowAni")
            if ani:
                self._anis.remove(ani)
                self._aniGroup.removeAnimation(ani)
                ani.deleteLater()

            return self._items.pop(index).widget()

        return None

    def removeWidget(self, widget):
        for i, item in enumerate(self._items):
            if item.widget() is widget:
                return self.takeAt(i)

    def removeAllWidgets(self):
        """Remove all widgets from layout."""
        while self._items:
            self.takeAt(0)

    def takeAllWidgets(self):
        """Remove all widgets from layout and delete them."""
        while self._items:
            w = self.takeAt(0)
            if w:
                w.deleteLater()

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        """Get the minimal height according to width."""
        return self._doLayout(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)

        if self.use_animation:
            self._deBounceTimer.start(80)
        else:
            self._doLayout(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())

        return size

    def setVerticalSpacing(self, spacing: int):
        """Set vertical spacing between widgets."""
        self._verticalSpacing = spacing

    def verticalSpacing(self):
        """Get vertical spacing between widgets."""
        return self._verticalSpacing

    def setHorizontalSpacing(self, spacing: int):
        """Set horizontal spacing between widgets."""
        self._horizontalSpacing = spacing

    def horizontalSpacing(self):
        """Get horizontal spacing between widgets."""
        return self._horizontalSpacing

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj in [w.widget() for w in self._items] and event.type() == QEvent.Type.ParentChange:
            self._wParent = obj.parent()
            obj.parent().installEventFilter(self)
            self._isInstalledEventFilter = True

        if obj == self._wParent and event.type() == QEvent.Type.Show:
            self._doLayout(self.geometry(), True)
            self._isInstalledEventFilter = True

        return super().eventFilter(obj, event)

    def _doLayout(self, rect: QRect, move: bool):
        """Adjust widgets position according to the window size."""
        aniRestart = False
        margin = self.contentsMargins()
        x = rect.x() + margin.left()
        y = rect.y() + margin.top()
        rowHeight = 0
        spaceX = self.horizontalSpacing()
        spaceY = self.verticalSpacing()

        for i, item in enumerate(self._items):
            if item.widget() and not item.widget().isVisible() and self.tight:
                continue

            nextX = x + item.sizeHint().width() + spaceX

            if nextX - spaceX > rect.right() - margin.right() and rowHeight > 0:
                x = rect.x() + margin.left()
                y = y + rowHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                rowHeight = 0

            if move:
                target = QRect(QPoint(x, y), item.sizeHint())
                if not self.use_animation:
                    item.setGeometry(target)
                elif target != self._anis[i].endValue():
                    self._anis[i].stop()
                    self._anis[i].setEndValue(target)
                    aniRestart = True

            x = nextX
            rowHeight = max(rowHeight, item.sizeHint().height())

        if self.use_animation and aniRestart:
            self._aniGroup.stop()
            self._aniGroup.start()

        return y + rowHeight + margin.bottom() - rect.y()


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

    from qtpy.QtWidgets import QPushButton

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(with_layout=False)
    flow_layout = QtAnimatedFlowLayout(frame, use_animation=True, tight=True)
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

    frame.show()
    sys.exit(app.exec_())
