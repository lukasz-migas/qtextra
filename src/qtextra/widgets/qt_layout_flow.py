"""Qt flow layout."""

from __future__ import annotations

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
from qtpy.QtWidgets import QLayout, QWidget, QWidgetItem
from superqt import QFlowLayout


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
        self._animations = []  # type: List[QPropertyAnimation]
        self._animation_group = QParallelAnimationGroup(self)
        self._y_spacing = 10
        self._x_spacing = 10
        self.duration = 300
        self.easing_curve = QEasingCurve.Type.Linear
        self.use_animation = use_animation
        self.tight = tight
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(lambda: self._doLayout(self.geometry(), True))
        self._parent = None
        self._has_event_filter = False

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
        if not self._has_event_filter:
            if w.parent():
                self._parent = w.parent()
                w.parent().installEventFilter(self)
            else:
                w.installEventFilter(self)

        if not self.use_animation:
            return

        ani = QPropertyAnimation(w, b"geometry")
        ani.setEndValue(QRect(QPoint(0, 0), w.size()))
        ani.setDuration(self.duration)
        ani.setEasingCurve(self.easing_curve)
        w.setProperty("flowAni", ani)
        self._animation_group.addAnimation(ani)

        if index == -1:
            self._animations.append(ani)
        else:
            self._animations.insert(index, ani)

    def setAnimation(self, duration: int, ease=QEasingCurve.Type.Linear):
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
        self.easing_curve = ease
        for animation in self._animations:
            animation.setDuration(duration)
            animation.setEasingCurve(ease)

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
                self._animations.remove(ani)
                self._animation_group.removeAnimation(ani)
                ani.deleteLater()

            return self._items.pop(index).widget()

        return None

    def removeWidget(self, widget):
        """Remove widget from layout."""
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
        """Get the expanding direction."""
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        """Check if the layout has height for width."""
        return True

    def heightForWidth(self, width: int):
        """Get the minimal height according to width."""
        return self._doLayout(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        if self.use_animation:
            self._debounce_timer.start(80)
        else:
            self._doLayout(rect, True)

    def sizeHint(self):
        """Get the size hint of the layout."""
        return self.minimumSize()

    def minimumSize(self):
        """Get the minimal size of the layout."""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def setVerticalSpacing(self, spacing: int):
        """Set vertical spacing between widgets."""
        self._y_spacing = spacing

    def verticalSpacing(self):
        """Get vertical spacing between widgets."""
        return self._y_spacing

    def setHorizontalSpacing(self, spacing: int):
        """Set horizontal spacing between widgets."""
        self._x_spacing = spacing

    def horizontalSpacing(self):
        """Get horizontal spacing between widgets."""
        return self._x_spacing

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj in [w.widget() for w in self._items] and event.type() == QEvent.Type.ParentChange:
            self._parent = obj.parent()
            obj.parent().installEventFilter(self)
            self._has_event_filter = True

        if obj == self._parent and event.type() == QEvent.Type.Show:
            self._doLayout(self.geometry(), True)
            self._has_event_filter = True

        return super().eventFilter(obj, event)

    def _doLayout(self, rect: QRect, move: bool):
        """Adjust widgets position according to the window size."""
        animation_restart = False
        margin = self.contentsMargins()
        x = rect.x() + margin.left()
        y = rect.y() + margin.top()
        row_height = 0
        space_x = self.horizontalSpacing()
        space_y = self.verticalSpacing()

        for i, item in enumerate(self._items):
            if item.widget() and not item.widget().isVisible() and self.tight:
                continue

            nextX = x + item.sizeHint().width() + space_x

            if nextX - space_x > rect.right() - margin.right() and row_height > 0:
                x = rect.x() + margin.left()
                y = y + row_height + space_y
                nextX = x + item.sizeHint().width() + space_x
                row_height = 0

            if move:
                target = QRect(QPoint(x, y), item.sizeHint())
                if not self.use_animation:
                    item.setGeometry(target)
                elif target != self._animations[i].endValue():
                    self._animations[i].stop()
                    self._animations[i].setEndValue(target)
                    animation_restart = True

            x = nextX
            row_height = max(row_height, item.sizeHint().height())

        if self.use_animation and animation_restart:
            self._animation_group.stop()
            self._animation_group.start()
        return y + row_height + margin.bottom() - rect.y()


class QtFlowLayout(QFlowLayout):
    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = -1):
        super().__init__(parent)
        if isinstance(margin, int):
            margin = (margin, margin, margin, margin)
        if margin:
            self.setContentsMargins(*margin)
        if spacing >= 0:
            self.setSpacing(spacing)

    def get_widget(self, index: int) -> QWidget | None:
        """Get widget at position."""
        item = self.itemAt(index)
        if not item:
            return None
        widget = item.widget()
        return widget

    def removeWidgetOrLayout(self, index: int) -> None:
        """Remove widget or layout based on index position."""
        widget = self.get_widget(index)
        if widget:
            self.removeWidget(widget)
            widget.deleteLater()

    def insertWidget(self, index: int, widget: QWidget) -> None:
        """Insert widget at specified position."""
        if index < 0:
            index = self.count()
        self.addWidget(widget)
        item = self._item_list.pop(len(self._item_list) - 1)
        self._item_list.insert(index, item)
        self.invalidate()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QPushButton

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(horz=False)
    flow_layout = QtAnimatedFlowLayout(None, use_animation=True, tight=True)
    flow_layout.setHorizontalSpacing(1)
    flow_layout.setVerticalSpacing(1)
    ha.addLayout(flow_layout)
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

    flow_layout = QtFlowLayout()
    flow_layout.setHorizontalSpacing(3)
    flow_layout.setVerticalSpacing(2)
    ha.addLayout(flow_layout)
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
