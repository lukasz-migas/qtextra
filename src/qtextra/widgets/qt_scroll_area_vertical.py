"""Vertical-only scroll area that never clips the width of its content."""

from __future__ import annotations

from qtpy.QtCore import QEvent, QObject, Qt
from qtpy.QtWidgets import QFrame, QScrollArea, QStyle, QWidget

# largest widget size allowed by Qt (QWIDGETSIZE_MAX)
QWIDGETSIZE_MAX = 16777215


class QtVerticalScrollArea(QScrollArea):
    """Vertical-only scroll area that always fits the full width of its widget.

    The width follows the widget's minimum width (never below ``min_width``/above ``max_width``, unless the content
    needs more), plus the scrollbar width while the scrollbar is shown, so the content is never clipped and there is
    no horizontal scrolling. The vertical scrollbar only appears once the area is shorter than the widget's minimum
    height (not its preferred height).
    """

    def __init__(
        self,
        widget: QWidget,
        parent: QWidget | None = None,
        min_width: int = 0,
        max_width: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._min_width = min_width
        self._max_width = max_width
        self.setFrameShape(QFrame.Shape.NoFrame)
        # the widget is sized manually, see `_update_widget_size`
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWidget(widget)
        self.verticalScrollBar().installEventFilter(self)
        self._update_width()

    def _scrollbar_width(self) -> int:
        """Width taken by the vertical scrollbar, or 0 when it is hidden or drawn over the content."""
        bar = self.verticalScrollBar()
        if not bar.isVisibleTo(self) or self.style().styleHint(QStyle.StyleHint.SH_ScrollBar_Transient, None, bar):
            return 0
        return bar.sizeHint().width()

    def _content_width(self) -> int:
        """Width the widget needs to be shown without clipping."""
        widget = self.widget()
        return max(self._min_width, widget.minimumSizeHint().width(), widget.minimumWidth()) if widget else 0

    def _update_width(self) -> None:
        """Make the area exactly wide enough for the content and the scrollbar."""
        content_width = self._content_width()
        bar_width = self._scrollbar_width()
        self.setMinimumWidth(content_width + bar_width)
        if self._max_width is not None:
            self.setMaximumWidth(min(max(self._max_width, content_width) + bar_width, QWIDGETSIZE_MAX))

    def _update_widget_size(self) -> None:
        """Fill the viewport width and only grow taller than the viewport when the content requires it."""
        widget = self.widget()
        if widget is None:
            return
        viewport = self.viewport().size()
        min_height = max(widget.minimumSizeHint().height(), widget.minimumHeight())
        widget.resize(viewport.width(), max(viewport.height(), min_height))

    def resizeEvent(self, event: QEvent) -> None:
        """Resize the content together with the area."""
        super().resizeEvent(event)
        self._update_widget_size()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Follow content layout changes and scrollbar visibility."""
        if obj is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self._update_width()
            self._update_widget_size()
        elif obj is self.verticalScrollBar() and event.type() in (QEvent.Type.Show, QEvent.Type.Hide):
            self._update_width()
        return super().eventFilter(obj, event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QPushButton, QVBoxLayout

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(horz=False)
    inner = QWidget()
    inner_layout = QVBoxLayout(inner)
    for i in range(30):
        inner_layout.addWidget(QPushButton(f"Button with a fairly long label {i}"))
    ha.addWidget(QtVerticalScrollArea(inner, min_width=200, max_width=300))
    frame.show()
    sys.exit(app.exec_())
