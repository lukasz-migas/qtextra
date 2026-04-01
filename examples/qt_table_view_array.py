"""QtArrayTableView."""

from __future__ import annotations

import numpy as np
from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_table_view_array import QtArrayTableView

N_ROWS = 500
N_COLS = 500


def _make_data() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.normal(size=(N_ROWS, N_COLS))


app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

status = QLabel(
    f"QtArrayTableView showing a {N_ROWS}x{N_COLS} float array with sorting, lazy row loading, and a colormap.",
)
table = QtArrayTableView(sortable=True)
table.set_data(
    _make_data(),
    fmt="{:.3f}",
    colormap="coolwarm",
    min_val=-2,
    max_val=2,
)

reload_button = QPushButton("Load New Data")
reload_button.clicked.connect(
    lambda: table.set_data(
        _make_data(),
        fmt="{:.3f}",
        colormap="coolwarm",
        min_val=-2,
        max_val=2,
    ),
)

layout.addWidget(status)
layout.addWidget(table)
layout.addWidget(reload_button)

widget.resize(900, 520)
widget.show()

app.exec_()
