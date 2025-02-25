from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from psygnal import Signal as PySignal
from qtpy.QtCore import QLineF, QPoint, QPointF, QRectF, Qt, Signal
from qtpy.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainterPath, QPen, QResizeEvent, QShowEvent, QWheelEvent
from qtpy.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem,
    QMenu,
    QWidgetAction,
)

from qtextra.utils.color import get_text_color
from qtextra.widgets._qt_graphics import QBaseGraphicsScene, QBaseGraphicsView
from qtextra.widgets.qt_line_edit import QDoubleLineEdit

if TYPE_CHECKING:
    import numpy.typing as npt


def quick_min_max(
    arr: npt.NDArray,
    down_sample_to: int = 1048576,
) -> tuple[float, float]:
    """Quickly compute the min and max of an array."""
    if arr.dtype.kind == "b":
        return 0.0, 1.0
    down_sample_factor = arr.size / down_sample_to
    if down_sample_factor <= 1.0:
        return arr.min(), arr.max()
    stride = int(np.ceil(down_sample_factor))
    arr_ref = arr[::stride]
    return arr_ref.min(), arr_ref.max()


class QHistogramView(QBaseGraphicsView):
    """Graphics view for displaying histograms and setting contrast limits."""

    evt_clim_changed = Signal(tuple)

    _pos_drag_start: QPoint | None = None
    _pos_drag_prev: QPoint | None = None

    def __init__(self):
        super().__init__()
        self._hist_items = [self.addItem(QHistogramItem())]
        self._line_low = self.addItem(QClimLineItem(0))
        self._line_low.evt_value_changed.connect(self._on_clim_changed)
        self._line_high = self.addItem(QClimLineItem(1))
        self._line_high.evt_value_changed.connect(self._on_clim_changed)
        self._view_range: tuple[float, float] = (0.0, 1.0)
        self._minmax = (0.0, 1.0)  # limits of the movable range

    def _on_clim_changed(self):
        clim = self.clim()
        if self._view_range is not None:
            v0, v1 = self._view_range
            x0, x1 = self.clim()
            if x0 < v0 or x1 > v1:
                self._view_range = clim
                self.update()
        self.evt_clim_changed.emit(clim)

    def clim(self) -> tuple[float, float]:
        """The current contrast limits."""
        return tuple(sorted([self._line_low.value(), self._line_high.value()]))

    def set_clim(self, clim: tuple[float, float]):
        """Set the contrast limits."""
        self._line_low.setValue(max(clim[0], self._minmax[0]))
        self._line_high.setValue(min(clim[1], self._minmax[1]))

    def set_minmax(self, minmax: tuple[float, float]):
        """Set the minimum and maximum values that the contrast limits can take."""
        self._minmax = minmax
        self._line_low.setRange(*minmax)
        self._line_high.setRange(*minmax)

    def set_histogram_from_array(
        self,
        arr: npt.NDArray,
        clim: tuple[float, float],
        is_rgb: bool = False,
        color: QColor = QColor(100, 100, 100),
        minmax: tuple[float, float] | None = None,
    ):
        """Set the histogram for an array."""
        # coerce the number of histogram items
        n_hist = 3 if is_rgb else 1
        for _ in range(n_hist, len(self._hist_items)):
            self.scene().removeItem(self._hist_items[-1])
            self._hist_items.pop()
        for _ in range(len(self._hist_items), n_hist):
            self._hist_items.append(self.addItem(QHistogramItem()))

        if is_rgb:
            brushes = [
                QBrush(QColor(255, 0, 0, 128)),
                QBrush(QColor(0, 255, 0, 128)),
                QBrush(QColor(0, 0, 255, 255)),
            ]  # RGB
            for i, (item, brush) in enumerate(zip(self._hist_items, brushes)):
                item.with_brush(brush).set_histogram_from_array(arr[:, :, i])
        else:
            brushes = [QBrush(color)]
            self._hist_items[0].with_brush(brushes[0]).set_histogram_from_array(arr)

        if not minmax:
            if arr.dtype.kind in "ui":
                minmax = (np.iinfo(arr.dtype).min, np.iinfo(arr.dtype).max)
            elif arr.dtype.kind == "b":
                minmax = (0, 1)
            else:
                minmax = clim
        self.set_minmax(minmax)
        self.set_clim(clim)
        if self._view_range is None:
            self._view_range = clim

    def setValueFormat(self, fmt: str):
        """Set the value format for the contrast limits."""
        self._line_low.setValueFormat(fmt)
        self._line_high.setValueFormat(fmt)

    def viewRect(self, width: float | None = None) -> QRectF:
        """The current view range as a QRectF."""
        x0, x1 = self._view_range
        if width is None:
            width = x1 - x0
        return QRectF(x0 - width * 0.03, 0, width * 1.06, 1)

    def set_view_range(self, x0: float, x1: float):
        """Set the view range."""
        if (x0, x1) == self._view_range:
            return
        self._view_range = (x0, x1)
        self.fitInView(self.viewRect(), Qt.AspectRatioMode.IgnoreAspectRatio)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.fitInView(self.viewRect(), Qt.AspectRatioMode.IgnoreAspectRatio)

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        x0, x1 = self.clim()
        self.fitInView(self.viewRect(x1 - x0), Qt.AspectRatioMode.IgnoreAspectRatio)
        self._line_low.setValue(self._line_low.value())
        self._line_high.setValue(self._line_high.value())

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        rect = self._line_low.boundingRect().united(self._line_high.boundingRect())
        for hist in self._hist_items:
            rect = rect.united(hist.boundingRect())
        x0, x1 = rect.left(), rect.right()
        self.fitInView(self.viewRect(x1 - x0), Qt.AspectRatioMode.IgnoreAspectRatio)
        self._view_range = (x0, x1)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.1
        else:
            factor = 1 / 1.1
        x0, x1 = self._view_range
        xcursor = self.mapToScene(event.pos()).x()
        x0 = max((x0 - xcursor) / factor + xcursor, self._minmax[0])
        x1 = min((x1 - xcursor) / factor + xcursor, self._minmax[1])
        self.set_view_range(x0, x1)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pos_drag_start = event.pos()
            self._pos_drag_prev = self._pos_drag_start
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.scene().grabSource():
            return super().mouseMoveEvent(event)
        if event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.pos()
            if self._pos_drag_prev is not None:
                delta = self.mapToScene(pos) - self.mapToScene(self._pos_drag_prev)
                delta = delta.x()
                x0, x1 = self._view_range
                x0 -= delta
                x1 -= delta
                self.set_view_range(x0, x1)
            self._pos_drag_prev = pos
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._pos_drag_start = None
        self._pos_drag_prev = None
        self.scene().setGrabSource(None)
        return super().mouseReleaseEvent(event)


class QClimLineItem(QGraphicsRectItem):
    """The line item for one of the contrast limits."""

    # NOTE: To properly set the bounding rect, we need to inherit from QGraphicsRectItem
    # with updated boundingRect method.
    evt_value_changed = PySignal(float)
    _Y_LOW = -1
    _Y_HIGH = 2
    _WIDTH_NORMAL = 3
    _WIDTH_HOVER = 6

    def __init__(self, x: float):
        super().__init__()
        self._color = QColor(255, 0, 0, 150)
        pen = QPen(self._color, self._WIDTH_NORMAL)
        pen.setCosmetic(True)
        self._qpen = pen
        self.setZValue(1000)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self._is_dragging = False
        self._range = (-float("inf"), float("inf"))
        self._value = x
        self._value_fmt = ".1f"
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self._value_label = QGraphicsSimpleTextItem()
        self._value_label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self._value_label.setFont(QFont("Arial", 12))
        self.setAcceptHoverEvents(True)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.scene().setGrabSource(self)
        elif event.buttons() & Qt.MouseButton.RightButton:
            self.scene().setGrabSource(self)
            menu = QClimMenu(self.scene().views()[0], self)
            menu._edit.setFocus()
            menu.exec(event.screenPos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self._is_dragging:
                self._drag_event(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        self._is_dragging = False
        self.scene().setGrabSource(None)
        self.setValue(event.pos().x())
        return super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        self._qpen.setWidthF(self._WIDTH_HOVER)
        self._show_value_label()
        self.update()
        return super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._qpen.setWidthF(self._WIDTH_NORMAL)
        self._value_label.hide()
        self.update()
        return super().hoverLeaveEvent(event)

    def _show_value_label(self):
        txt = format(self.value(), self._value_fmt)
        self._value_label.setText(txt)
        vp = self.scene().views()[0].viewport()
        background_color = vp.palette().color(vp.backgroundRole())
        self._value_label.setBrush(QBrush(get_text_color(background_color)))
        text_width = self._value_label.boundingRect().width()
        pos = QPointF(self.value(), 0)
        if pos.x() + text_width / self._x_scale() > self._range[1]:
            pos.setX(pos.x() - (text_width + 4) / self._x_scale())
        else:
            pos.setX(pos.x() + 4 / self._x_scale())
        self._value_label.setPos(self.mapToScene(pos))
        if self._value_label.scene() is None:
            # prevent scene movement during adding the label
            rect = self.scene().sceneRect()
            self.scene().addItem(self._value_label)
            self.scene().setSceneRect(rect)
        self._value_label.show()

    def _drag_event(self, event: QGraphicsSceneMouseEvent):
        self.setValue(event.pos().x())
        self._show_value_label()
        if scene := self.scene():
            scene.update()

    def setValueFormat(self, fmt: str):
        self._value_fmt = fmt

    def paint(self, painter, option, widget):
        painter.setPen(self._qpen)
        start = QPointF(self._value, self._Y_LOW)
        end = QPointF(self._value, self._Y_HIGH)
        line = QLineF(start, end)
        painter.drawLine(line)

    def value(self) -> float:
        """The x value of the line (the contrast limit)."""
        return self._value

    def setValue(self, x: float):
        """Set the x value of the line (the contrast limit)."""
        old_bbox = self.boundingRect()
        old_value = self._value
        new_value = min(max(x, self._range[0]), self._range[1])
        self._value = new_value
        new_bbox = self.boundingRect()
        self.setRect(new_bbox)
        if new_value != old_value:
            self.evt_value_changed.emit(self._value)
        if scene := self.scene():
            scene.update(self.mapRectToScene(old_bbox.united(new_bbox)))

    def setRange(self, low: float, high: float):
        """Set the min/max range of the line x value."""
        self._range = (low, high)
        if not low <= self.value() <= high:
            self.setValue(self.value())

    def scene(self) -> QBaseGraphicsScene:
        return super().scene()

    def _x_scale(self) -> float:
        return self.view().transform().m11()

    def view(self) -> QHistogramView:
        return self.scene().views()[0]

    def boundingRect(self):
        w = 10.0 / self._x_scale()
        x = self.value()
        return QRectF(x - w / 2, self._Y_LOW, w, self._Y_HIGH - self._Y_LOW)


class QHistogramItem(QGraphicsPathItem):
    """The histogram item."""

    def __init__(self):
        super().__init__()
        self._hist_path = QPainterPath()
        self._hist_brush = QBrush(QColor(100, 100, 100))
        self.setPen(QPen(QColor(0, 0, 0, 0)))

    def with_brush(self, brush: QBrush) -> QHistogramItem:
        """Set the brush for the histogram."""
        self._hist_brush = brush
        return self

    def set_histogram_from_array(self, arr: npt.NDArray) -> tuple[float, float]:
        """Set the histogram from an array."""
        _min, _max = quick_min_max(arr)
        if arr.dtype in ("uint8", "uint8"):
            _nbin = 64
        else:
            _nbin = 256
        _nbin = min(_nbin, int(np.prod(arr.shape[-2:])) // 2)
        # draw histogram
        if arr.dtype.kind == "b":
            edges = np.array([0, 0.5, 1])
            frac_true = np.sum(arr) / arr.size
            hist = np.array([1 - frac_true, frac_true])
        elif _max > _min:
            arr = arr.clip(_min, _max)
            if arr.dtype.kind in "ui" and _max - _min < _nbin:
                # bin number is excessive
                _nbin = int(_max - _min)
                normed = (arr - _min).astype(np.uint8)
            else:
                normed = ((arr - _min) / (_max - _min) * _nbin).astype(np.uint8)
            hist = np.bincount(normed.ravel(), minlength=_nbin)
            hist = hist / hist.max()
            edges = np.linspace(_min, _max, _nbin + 1)
        else:
            edges = np.array([_min, _max])
            hist = np.zeros(1)
        _path = QPainterPath()
        self.setBrush(self._hist_brush)
        _path.moveTo(edges[0], 1)
        for e0, e1, h in zip(edges[:-1], edges[1:], hist):
            _path.lineTo(e0, 1 - h)
            _path.lineTo(e1, 1 - h)
        _path.lineTo(edges[-1], 1)
        _path.closeSubpath()
        self.setPath(_path)
        self.update()


class QClimMenu(QMenu):
    """Menu."""

    def __init__(self, parent: QHistogramView, item: QClimLineItem):
        super().__init__(parent)
        self._hist_view = parent
        self._item = item
        self._edit = QDoubleLineEdit()
        self._edit.setText(format(item.value(), item._value_fmt))
        self._edit.valueChanged.connect(self._on_value_changed)
        self._edit.editingFinished.connect(self._on_value_set)
        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(self._edit)
        self.addAction(widget_action)

    def _on_value_changed(self):
        """Value changed."""
        value = self._edit.text()
        if value:
            value = float(value)
            self._item.setValue(value)

    def _on_value_set(self):
        value = self._edit.text()
        if value:
            value = float(value)
            self._item.setValue(value)
            # update min/max
            if value < self._hist_view._minmax[0]:
                self._hist_view.set_minmax((value, self._hist_view._minmax[1]))
            elif value > self._hist_view._minmax[1]:
                self._hist_view.set_minmax((self._hist_view._minmax[0], value))
            # update view range
            v0, v1 = self._hist_view._view_range
            if value < v0:
                self._hist_view.set_view_range(value, v1)
            elif value > v1:
                self._hist_view.set_view_range(v0, value)
        self.close()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(horz=False)
    frame.setMinimumSize(600, 600)
    hist = QHistogramView()
    hist.set_histogram_from_array(np.random.randint(0, 65332, 100), (0, 65332), minmax=(0, 65332))
    ha.addWidget(hist)

    hist = QHistogramView()
    hist.set_histogram_from_array(np.random.randint(0, 255, (100, 100, 3)), (0, 255), is_rgb=True, minmax=(0, 255))
    ha.addWidget(hist)

    frame.show()
    sys.exit(app.exec_())
