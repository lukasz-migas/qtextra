"""Vertical-only scroll area that never clips the width of its content."""

from __future__ import annotations

from qtpy.QtCore import QEvent, QObject, Qt, QTimer
from qtpy.QtWidgets import QFrame, QScrollArea, QScrollBar, QSplitter, QWidget

# largest widget size allowed by Qt (QWIDGETSIZE_MAX)
QWIDGETSIZE_MAX = 16777215


class QtVerticalScrollArea(QScrollArea):
    """Vertical-only scroll area that always fits the full width of its widget.

    The width follows the widget's minimum width (never below ``min_width``/above ``max_width``, unless the content
    needs more), so the content is never clipped and there is no horizontal scrolling. The vertical scrollbar is drawn
    on top of the content (overlay) so it never takes any width, and only appears once the area is shorter than the
    widget's minimum height (not its preferred height).
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
        # the native scrollbar is hidden (it keeps its range/value) and mirrored by an overlay scrollbar
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidget(widget)
        widget.installEventFilter(self)

        self._overlay_bar = QScrollBar(Qt.Orientation.Vertical, self)
        self._overlay_bar.hide()
        native = self.verticalScrollBar()
        native.rangeChanged.connect(self._sync_overlay_range)
        native.valueChanged.connect(self._overlay_bar.setValue)
        self._overlay_bar.valueChanged.connect(native.setValue)
        self._update_width()

    def _content_width(self) -> int:
        """Width the widget needs to be shown without clipping."""
        widget = self.widget()
        return max(self._min_width, widget.minimumSizeHint().width(), widget.minimumWidth()) if widget else 0

    def _update_width(self) -> None:
        """Make the area exactly wide enough for the content."""
        content_width = self._content_width()
        self.setMinimumWidth(content_width)
        if self._max_width is not None:
            self.setMaximumWidth(min(max(self._max_width, content_width), QWIDGETSIZE_MAX))
        QTimer.singleShot(0, self._rebalance_splitter)

    def _rebalance_splitter(self) -> None:
        """Hand space back to the sibling panes when a parent splitter left this area wider than allowed.

        A splitter only clamps the area to its new limits, it keeps its own stale pane size, which leaves an empty
        strip next to the content until the user touches the handle.
        """
        splitter = self.parent()
        if not isinstance(splitter, QSplitter) or splitter.orientation() != Qt.Orientation.Horizontal:
            return
        index = splitter.indexOf(self)
        sizes = splitter.sizes()
        if index < 0 or len(sizes) < 2:
            return
        target = min(max(sizes[index], self.minimumWidth()), self.maximumWidth())
        excess = sizes[index] - target
        if not excess:
            return
        sizes[index] = target
        others = [i for i in range(len(sizes)) if i != index]
        sizes[max(others, key=lambda i: sizes[i])] += excess
        splitter.setSizes(sizes)

    def _update_widget_size(self) -> None:
        """Fill the viewport width and only grow taller than the viewport when the content requires it."""
        widget = self.widget()
        if widget is None:
            return
        viewport = self.viewport().size()
        min_height = max(widget.minimumSizeHint().height(), widget.minimumHeight())
        widget.resize(viewport.width(), max(viewport.height(), min_height))

    def _sync_overlay_range(self, minimum: int, maximum: int) -> None:
        """Mirror the native scrollbar range on the overlay scrollbar and show it only when scrolling is possible."""
        native = self.verticalScrollBar()
        self._overlay_bar.setRange(minimum, maximum)
        self._overlay_bar.setPageStep(native.pageStep())
        self._overlay_bar.setVisible(maximum > minimum)
        self._overlay_bar.raise_()

    def _place_overlay(self) -> None:
        """Dock the overlay scrollbar to the right edge of the area."""
        width = self._overlay_bar.sizeHint().width()
        self._overlay_bar.setGeometry(self.width() - width, 0, width, self.height())
        self._overlay_bar.setPageStep(self.verticalScrollBar().pageStep())

    def resizeEvent(self, event: QEvent) -> None:
        """Resize the content together with the area."""
        super().resizeEvent(event)
        self._update_widget_size()
        self._place_overlay()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Follow content layout changes."""
        if obj is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self._update_width()
            self._update_widget_size()
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
