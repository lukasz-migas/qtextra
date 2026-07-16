"""Tests for the native polygon view."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from qtpy.QtCore import QPointF
from qtpy.QtGui import QColor, QImage, QPainter
from qtpy.QtWidgets import QWidget

from qtextra.widgets.qt_polygon import QPolygonView


def _square(y: float = 0.0, x: float = 0.0, size: float = 10.0) -> np.ndarray:
    return np.array(
        [
            [y, x],
            [y, x + size],
            [y + size, x + size],
            [y + size, x],
        ],
        dtype=np.float64,
    )


def test_polygon_view_accepts_numpy_and_python_coordinates(qtbot: Any) -> None:
    widget = QPolygonView()
    qtbot.addWidget(widget)

    widget.set_shape(np.array([[10, 2], [10, 7], [30, 7], [30, 2]]))

    assert widget.shape_count() == 1
    assert widget._item.boundingRect().getRect() == (2.0, 10.0, 5.0, 20.0)
    assert widget._item._paths[0].contains(QPointF(4.0, 20.0))

    widget.set_shape([(1, 3), (1, 8), (5, 8), (5, 3), (1, 3)])

    assert widget.shape_count() == 1
    assert widget._item.boundingRect().getRect() == (3.0, 1.0, 5.0, 4.0)


def test_polygon_view_supports_multiple_polygons_and_holes(qtbot: Any) -> None:
    widget = QPolygonView()
    qtbot.addWidget(widget)
    exterior = _square()
    hole = _square(3, 3, 4)

    widget.set_shapes([exterior, _square(20, 20)], holes=[[hole], None])

    first_path = widget._item._paths[0]
    assert widget.shape_count() == 2
    assert first_path.contains(QPointF(1, 1))
    assert not first_path.contains(QPointF(5, 5))
    assert widget._item.boundingRect().getRect() == (0.0, 0.0, 30.0, 30.0)


def test_polygon_view_applies_global_and_per_shape_colors(qtbot: Any) -> None:
    widget = QPolygonView([_square(), _square(x=20)], face_color="#112233", edge_color="#abcdef")
    qtbot.addWidget(widget)

    assert widget._item._batch_count == 1
    assert widget._item._face_colors == [QColor("#112233"), QColor("#112233")]
    assert widget._item._edge_colors == [QColor("#abcdef"), QColor("#abcdef")]

    widget.set_face_colors(["#ff0000", None])
    widget.set_edge_colors([None, "#00ff00"])

    assert widget._item._batch_count == 2
    assert widget._item._face_colors == [QColor("#ff0000"), None]
    assert widget._item._edge_colors == [None, QColor("#00ff00")]

    widget.set_face_color(None)
    widget.set_edge_color(None)

    assert widget._item._batch_count == 0


def test_replacing_shapes_preserves_global_colors_and_clears_overrides(qtbot: Any) -> None:
    widget = QPolygonView([_square(), _square(x=20)], face_color="red", edge_color="blue")
    qtbot.addWidget(widget)
    widget.set_face_colors(["green", "yellow"])
    widget.set_edge_colors([None, "black"])

    widget.set_shapes([_square(), _square(x=20), _square(x=40)])

    assert widget._item._face_colors == [QColor("red")] * 3
    assert widget._item._edge_colors == [QColor("blue")] * 3


@pytest.mark.parametrize(
    ("coordinates", "message"),
    [
        ([[0, 0], [1, 1]], "at least three"),
        ([[0, 0, 1], [1, 1, 2], [2, 2, 3]], "shape"),
        ([[0, 0], [1, np.nan], [2, 0]], "finite"),
        ([[0, 0], [1, 1], [2, 2]], "non-zero area"),
    ],
)
def test_polygon_view_rejects_invalid_geometry(qtbot: Any, coordinates: list[list[float]], message: str) -> None:
    widget = QPolygonView(_square())
    qtbot.addWidget(widget)
    original_path = widget._item._paths[0]

    with pytest.raises(ValueError, match=message):
        widget.set_shape(coordinates)

    assert widget.shape_count() == 1
    assert widget._item._paths[0] is original_path


def test_polygon_view_rejects_invalid_styles_without_mutation(qtbot: Any) -> None:
    widget = QPolygonView([_square(), _square(x=20)], face_color="red", edge_width=2.0)
    qtbot.addWidget(widget)

    with pytest.raises(ValueError, match="2 entries"):
        widget.set_face_colors(["blue"])
    with pytest.raises(ValueError, match="Invalid edge color"):
        widget.set_edge_color("not-a-color")
    with pytest.raises(ValueError, match="non-negative finite"):
        widget.set_edge_width(-1)

    assert widget._item._face_colors == [QColor("red"), QColor("red")]
    assert widget._item._edge_width == 2.0


def test_polygon_view_resizes_without_rebuilding_cached_geometry(qtbot: Any) -> None:
    widget = QPolygonView(_square())
    qtbot.addWidget(widget)
    widget.resize(200, 100)
    widget.show()
    qtbot.waitExposed(widget)
    path = widget._item._paths[0]
    picture = widget._item._picture

    widget.resize(600, 300)
    qtbot.wait(10)

    assert widget._item._paths[0] is path
    assert widget._item._picture is picture
    assert widget.transform().m11() == pytest.approx(widget.transform().m22())


def test_polygon_view_clear_and_parent(qtbot: Any) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    widget = QPolygonView(_square(), parent=parent)

    widget.clear()

    assert widget.parent() is parent
    assert widget.shape_count() == 0
    assert widget.scene().sceneRect().isEmpty()


def test_polygon_view_caches_ten_thousand_polygons_in_one_scene_item(qtbot: Any) -> None:
    coordinates = np.arange(100, dtype=np.float64)
    yy, xx = np.meshgrid(coordinates, coordinates, indexing="ij")
    origins = np.column_stack((yy.ravel(), xx.ravel())) * 2.0
    unit_square = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=np.float64)
    shapes = origins[:, None, :] + unit_square[None, :, :]
    widget = QPolygonView()
    qtbot.addWidget(widget)

    widget.set_shapes(shapes)
    widget.resize(640, 480)
    widget.show()
    qtbot.waitExposed(widget)
    image = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    widget.render(painter)
    painter.end()

    assert widget.shape_count() == 10_000
    assert len(widget.scene().items()) == 1
    assert widget._item._batch_count == 1
    assert not image.isNull()
