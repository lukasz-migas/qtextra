"""Native Qt widget for displaying collections of two-dimensional polygons."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

import numpy as np
from qtpy.QtCore import QPointF, QRectF, Qt
from qtpy.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPicture, QPolygonF, QResizeEvent, QShowEvent
from qtpy.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from qtextra.widgets._qt_graphics import QBaseGraphicsView

Color: TypeAlias = QColor | str | None
Ring: TypeAlias = np.ndarray | Sequence[Sequence[float]]
Rings: TypeAlias = Ring | Sequence[Ring]

DEFAULT_EDGE_COLOR = QColor(128, 128, 128)
DEFAULT_EDGE_WIDTH = 1.0
VIEW_PADDING = 0.03


def _normalize_color(color: Color, name: str) -> QColor | None:
    if color is None:
        return None
    normalized = QColor(color)
    if not normalized.isValid():
        raise ValueError(f"Invalid {name}: {color}")
    return normalized


def _normalize_ring(ring: Ring, name: str) -> np.ndarray:
    try:
        coordinates = np.asarray(ring, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain numeric (y, x) coordinates") from exc
    if coordinates.ndim != 2 or coordinates.shape[1] != 2:
        raise ValueError(f"{name} must have shape (N, 2), received {coordinates.shape}")
    if len(coordinates) < 3:
        raise ValueError(f"{name} must contain at least three coordinates")
    if not np.all(np.isfinite(coordinates)):
        raise ValueError(f"{name} must contain only finite coordinates")
    if np.array_equal(coordinates[0], coordinates[-1]):
        coordinates = coordinates[:-1]
        if len(coordinates) < 3:
            raise ValueError(f"{name} must contain at least three distinct coordinates")
    if np.isclose(_signed_area_twice(coordinates), 0.0):
        raise ValueError(f"{name} must enclose a non-zero area")
    return np.ascontiguousarray(coordinates)


def _normalize_rings(rings: Rings | None, name: str) -> list[np.ndarray]:
    if rings is None:
        return []
    if isinstance(rings, np.ndarray):
        if rings.ndim == 2:
            return [_normalize_ring(rings, name)]
        if rings.ndim == 3:
            return [_normalize_ring(ring, f"{name}[{index}]") for index, ring in enumerate(rings)]
        raise ValueError(f"{name} must have shape (N, 2) or (M, N, 2), received {rings.shape}")
    if isinstance(rings, Sequence) and not isinstance(rings, (str, bytes)) and len(rings) == 0:
        return []
    try:
        array = np.asarray(rings)
    except (TypeError, ValueError):
        array = None
    if array is not None and array.ndim == 2 and array.shape[1:] == (2,):
        return [_normalize_ring(rings, name)]
    if not isinstance(rings, Sequence) or isinstance(rings, (str, bytes)):
        raise TypeError(f"{name} must be a coordinate ring or a sequence of rings")
    return [_normalize_ring(ring, f"{name}[{index}]") for index, ring in enumerate(rings)]


def _signed_area_twice(coordinates: np.ndarray) -> float:
    y = coordinates[:, 0]
    x = coordinates[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _ring_polygon(coordinates: np.ndarray, *, exterior: bool) -> QPolygonF:
    area = _signed_area_twice(coordinates)
    if (exterior and area < 0.0) or (not exterior and area > 0.0):
        coordinates = coordinates[::-1]
    return QPolygonF([QPointF(float(x), float(y)) for y, x in coordinates])


def _polygon_path(exterior: np.ndarray, holes: Sequence[np.ndarray]) -> QPainterPath:
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    path.addPolygon(_ring_polygon(exterior, exterior=True))
    path.closeSubpath()
    for hole in holes:
        path.addPolygon(_ring_polygon(hole, exterior=False))
        path.closeSubpath()
    return path


class _PolygonGraphicsItem(QGraphicsItem):
    """Render cached polygon paths as a single graphics-scene item."""

    def __init__(self) -> None:
        super().__init__()
        self._paths: list[QPainterPath] = []
        self._face_colors: list[QColor | None] = []
        self._edge_colors: list[QColor | None] = []
        self._edge_width = DEFAULT_EDGE_WIDTH
        self._bounds = QRectF()
        self._picture = QPicture()
        self._batch_count = 0

    def boundingRect(self) -> QRectF:
        """Return the complete polygon extent in scene coordinates."""
        return QRectF(self._bounds)

    def paint(
        self,
        painter: QPainter,
        _option: QStyleOptionGraphicsItem,
        _widget: QWidget | None = None,
    ) -> None:
        """Replay the cached vector paint commands."""
        painter.drawPicture(0, 0, self._picture)

    def set_geometry(self, paths: list[QPainterPath], bounds: QRectF) -> None:
        """Replace the cached polygon geometry."""
        self.prepareGeometryChange()
        self._paths = paths
        self._bounds = QRectF(bounds)
        self.update()

    def set_style(
        self,
        face_colors: list[QColor | None],
        edge_colors: list[QColor | None],
        edge_width: float,
    ) -> None:
        """Replace the polygon styles and rebuild the vector picture."""
        self._face_colors = face_colors
        self._edge_colors = edge_colors
        self._edge_width = edge_width
        self._rebuild_picture()
        self.update()

    def _rebuild_picture(self) -> None:
        picture = QPicture()
        painter = QPainter(picture)
        self._batch_count = 0
        current_key: tuple[int | None, int | None] | None = None
        current_path: QPainterPath | None = None

        def draw_batch(key: tuple[int | None, int | None], path: QPainterPath) -> None:
            face_rgba, edge_rgba = key
            if face_rgba is None:
                painter.setBrush(Qt.BrushStyle.NoBrush)
            else:
                painter.setBrush(QBrush(QColor.fromRgba(face_rgba)))
            if edge_rgba is None:
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                pen = QPen(QColor.fromRgba(edge_rgba), self._edge_width)
                pen.setCosmetic(True)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
            painter.drawPath(path)
            self._batch_count += 1

        for path, face_color, edge_color in zip(self._paths, self._face_colors, self._edge_colors):
            key = (
                None if face_color is None else face_color.rgba(),
                None if edge_color is None else edge_color.rgba(),
            )
            if key == (None, None):
                continue
            if current_path is None or key != current_key:
                if current_path is not None and current_key is not None:
                    draw_batch(current_key, current_path)
                current_key = key
                current_path = QPainterPath()
                current_path.setFillRule(Qt.FillRule.WindingFill)
            current_path.addPath(path)
        if current_path is not None and current_key is not None:
            draw_batch(current_key, current_path)
        painter.end()
        self._picture = picture


class QPolygonView(QBaseGraphicsView):
    """Display one or more closed polygons using native Qt vector painting."""

    def __init__(
        self,
        shapes: Rings | None = None,
        *,
        face_color: Color = None,
        edge_color: Color = DEFAULT_EDGE_COLOR,
        edge_width: float = DEFAULT_EDGE_WIDTH,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the polygon view with optional coordinate data."""
        super().__init__(parent)
        self._item = self.addItem(_PolygonGraphicsItem())
        self._global_face_color = _normalize_color(face_color, "face color")
        self._global_edge_color = _normalize_color(edge_color, "edge color")
        self._face_colors: list[QColor | None] | None = None
        self._edge_colors: list[QColor | None] | None = None
        self._edge_width = self._normalize_edge_width(edge_width)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setInteractive(False)
        if shapes is not None:
            self.set_shapes(shapes)
        else:
            self._apply_style()

    def shape_count(self) -> int:
        """Return the number of polygons currently displayed."""
        return len(self._item._paths)

    def set_shape(self, exterior: Ring, *, holes: Rings | None = None) -> None:
        """Replace the view contents with one exterior ring and optional holes."""
        normalized_exterior = _normalize_ring(exterior, "exterior")
        normalized_holes = _normalize_rings(holes, "holes")
        self._set_normalized_shapes([normalized_exterior], [normalized_holes])

    def set_shapes(
        self,
        exteriors: Rings,
        *,
        holes: Sequence[Rings | None] | None = None,
    ) -> None:
        """Replace the displayed polygons and their optional aligned hole groups."""
        normalized_exteriors = _normalize_rings(exteriors, "exteriors")
        if holes is None or len(holes) == 0:
            normalized_holes = [[] for _ in normalized_exteriors]
        else:
            if len(holes) != len(normalized_exteriors):
                raise ValueError(
                    f"holes must have one entry per polygon: expected {len(normalized_exteriors)}, received {len(holes)}"
                )
            normalized_holes = [
                _normalize_rings(polygon_holes, f"holes[{index}]") for index, polygon_holes in enumerate(holes)
            ]
        self._set_normalized_shapes(normalized_exteriors, normalized_holes)

    def clear(self) -> None:
        """Remove all displayed polygons."""
        self._set_normalized_shapes([], [])

    def set_face_color(self, color: Color) -> None:
        """Set one fill color for every polygon and clear per-polygon overrides."""
        normalized = _normalize_color(color, "face color")
        self._global_face_color = normalized
        self._face_colors = None
        self._apply_style()

    def set_edge_color(self, color: Color) -> None:
        """Set one outline color for every polygon and clear per-polygon overrides."""
        normalized = _normalize_color(color, "edge color")
        self._global_edge_color = normalized
        self._edge_colors = None
        self._apply_style()

    def set_face_colors(self, colors: Sequence[Color]) -> None:
        """Set fill colors aligned one-to-one with the displayed polygons."""
        self._face_colors = self._normalize_color_sequence(colors, "face colors")
        self._apply_style()

    def set_edge_colors(self, colors: Sequence[Color]) -> None:
        """Set outline colors aligned one-to-one with the displayed polygons."""
        self._edge_colors = self._normalize_color_sequence(colors, "edge colors")
        self._apply_style()

    def set_edge_width(self, width: float) -> None:
        """Set the outline width in screen pixels."""
        self._edge_width = self._normalize_edge_width(width)
        self._apply_style()

    def fit_to_view(self) -> None:
        """Fit the complete polygon extent into the viewport while preserving aspect ratio."""
        bounds = self._item.boundingRect()
        if bounds.isEmpty():
            self.resetTransform()
            self.scene().setSceneRect(QRectF())
            return
        padding = max(bounds.width(), bounds.height()) * VIEW_PADDING
        view_rect = bounds.adjusted(-padding, -padding, padding, padding)
        self.scene().setSceneRect(view_rect)
        self.fitInView(view_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Refit cached geometry after the viewport size changes."""
        super().resizeEvent(event)
        self.fit_to_view()

    def showEvent(self, event: QShowEvent) -> None:
        """Fit geometry once the widget has a usable viewport."""
        super().showEvent(event)
        self.fit_to_view()

    def _set_normalized_shapes(
        self,
        exteriors: Sequence[np.ndarray],
        holes: Sequence[Sequence[np.ndarray]],
    ) -> None:
        paths = [_polygon_path(exterior, polygon_holes) for exterior, polygon_holes in zip(exteriors, holes)]
        bounds = QRectF()
        for path in paths:
            path_bounds = path.controlPointRect()
            bounds = path_bounds if bounds.isNull() else bounds.united(path_bounds)
        self._face_colors = None
        self._edge_colors = None
        self._item.set_geometry(paths, bounds)
        self._apply_style()
        self.fit_to_view()

    def _apply_style(self) -> None:
        count = self.shape_count()
        face_colors = self._face_colors or [self._global_face_color] * count
        edge_colors = self._edge_colors or [self._global_edge_color] * count
        self._item.set_style(face_colors, edge_colors, self._edge_width)

    def _normalize_color_sequence(self, colors: Sequence[Color], name: str) -> list[QColor | None]:
        if isinstance(colors, (str, bytes, QColor)):
            raise TypeError(f"{name} must be a sequence; use the singular color setter for one color")
        if len(colors) != self.shape_count():
            raise ValueError(f"{name} must contain {self.shape_count()} entries, received {len(colors)}")
        return [_normalize_color(color, f"{name}[{index}]") for index, color in enumerate(colors)]

    @staticmethod
    def _normalize_edge_width(width: float) -> float:
        try:
            normalized = float(width)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"edge width must be a non-negative finite number: {width}") from exc
        if not np.isfinite(normalized) or normalized < 0.0:
            raise ValueError(f"edge width must be a non-negative finite number: {width}")
        return normalized


if __name__ == "__main__":  # pragma: no cover
    from qtextra.utils.dev import qframe

    app, frame, layout = qframe(horz=False)
    polygon_view = QPolygonView(face_color="#803498db", edge_color="#1f618d", edge_width=2.0)
    polygon_view.set_shape(
        [(0, 0), (0, 10), (10, 10), (10, 0)],
        holes=[[(3, 3), (3, 7), (7, 7), (7, 3)]],
    )
    layout.addWidget(polygon_view)
    frame.resize(600, 400)
    frame.show()
    app.exec_()
