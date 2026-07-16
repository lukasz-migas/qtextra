"""Show native polygon views at different widget sizes."""

from __future__ import annotations

import numpy as np

from qtextra.utils.dev import qframe
from qtextra.widgets.qt_polygon import QPolygonView


def square(y: float, x: float, size: float) -> np.ndarray:
    """Return one square as (y, x) coordinates."""
    return np.array([[y, x], [y, x + size], [y + size, x + size], [y + size, x]], dtype=float)


app, frame, layout = qframe(horz=True, add_reload=False, dev=False)
shapes = [
    square(0, 0, 20),
    np.array([[2, 28], [8, 47], [22, 42], [18, 25]], dtype=float),
    np.array([[28, 5], [26, 20], [35, 27], [48, 17], [44, 2]], dtype=float),
]
holes = [[square(6, 6, 8)], None, None]

outline_view = QPolygonView(edge_color="#607d8b", edge_width=2.0)
outline_view.set_shapes(shapes, holes=holes)
outline_view.setFixedSize(180, 180)
layout.addWidget(outline_view)

filled_view = QPolygonView(edge_width=2.0)
filled_view.set_shapes(shapes, holes=holes)
filled_view.set_face_colors(["#803498db", "#80e67e22", "#802ecc71"])
filled_view.set_edge_colors(["#1f618d", "#a04000", "#196f3d"])
layout.addWidget(filled_view)

frame.resize(800, 500)
frame.show()
app.exec_()
