"""Display thousands of polygons and report native Qt rendering timings."""

from __future__ import annotations

from time import perf_counter

import numpy as np
from qtpy.QtCore import Signal
from qtpy.QtGui import QPaintEvent
from qtpy.QtWidgets import QLabel

from qtextra.utils.dev import qframe
from qtextra.widgets.qt_polygon import QPolygonView

N_ROWS = 100
N_COLUMNS = 100
N_VERTICES = 10


class _TimedPolygonView(QPolygonView):
    """Polygon view that reports the duration of each paint event."""

    evt_painted = Signal(float)

    def paintEvent(self, event: QPaintEvent) -> None:
        start = perf_counter()
        super().paintEvent(event)
        self.evt_painted.emit((perf_counter() - start) * 1_000.0)


def make_cell_shapes(
    rows: int = N_ROWS,
    columns: int = N_COLUMNS,
    vertices: int = N_VERTICES,
    seed: int = 42,
) -> np.ndarray:
    """Generate a regular field of irregular cell-like polygon coordinates."""
    rng = np.random.default_rng(seed)
    angles = np.linspace(0.0, 2.0 * np.pi, vertices, endpoint=False)
    radii = rng.uniform(0.34, 0.48, size=(rows * columns, vertices))
    center_y, center_x = np.meshgrid(
        np.arange(rows, dtype=np.float64),
        np.arange(columns, dtype=np.float64),
        indexing="ij",
    )
    centers = np.column_stack((center_y.ravel(), center_x.ravel()))
    offsets = np.stack((np.sin(angles), np.cos(angles)), axis=-1)
    return centers[:, None, :] + radii[:, :, None] * offsets[None, :, :]


def main() -> None:
    """Create and show the polygon performance example."""
    app, frame, layout = qframe(horz=False, add_reload=False, dev=False)
    timing_label = QLabel()
    layout.addWidget(timing_label)

    generation_start = perf_counter()
    shapes = make_cell_shapes()
    generation_ms = (perf_counter() - generation_start) * 1_000.0

    polygon_view = _TimedPolygonView(
        face_color="#403f51b5",
        edge_color="#5c6bc0",
        edge_width=1.0,
    )
    load_start = perf_counter()
    polygon_view.set_shapes(shapes)
    load_ms = (perf_counter() - load_start) * 1_000.0
    layout.addWidget(polygon_view)

    def update_timings(paint_ms: float) -> None:
        timing_label.setText(
            f"{len(shapes):,} polygons with {shapes.shape[1]} vertices each | "
            f"generate: {generation_ms:.1f} ms | set_shapes: {load_ms:.1f} ms | last paint: {paint_ms:.1f} ms"
        )

    polygon_view.evt_painted.connect(update_timings)
    update_timings(0.0)
    frame.resize(1000, 800)
    frame.setWindowTitle("QPolygonView performance")
    frame.show()
    app.exec_()


if __name__ == "__main__":
    main()
