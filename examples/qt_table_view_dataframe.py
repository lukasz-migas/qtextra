"""QtDataFrameWidget."""

from __future__ import annotations

import numpy as np
import pandas as pd
from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_table_view_dataframe import QtDataFrameWidget

try:
    import polars as pl
except ImportError:
    pl = None

N_ROWS = 500
N_COLS = 500


def _make_pandas_frame() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    columns = [f"feature_{i:03d}" for i in range(N_COLS)]
    index = [f"sample_{i:03d}" for i in range(N_ROWS)]
    values = rng.normal(loc=10, scale=2, size=(N_ROWS, N_COLS))
    return pd.DataFrame(values, index=index, columns=columns)


def _make_pandas_multiindex() -> pd.DataFrame:
    rng = np.random.default_rng(123)
    columns = pd.MultiIndex.from_tuples(
        [(f"metric_{i // 10:02d}", f"stat_{i % 10:02d}") for i in range(N_COLS)],
        names=["metric", "stat"],
    )
    index = pd.MultiIndex.from_tuples(
        [(f"sample_{i // 10:02d}", f"rep_{i % 10:02d}") for i in range(N_ROWS)],
        names=["sample", "replicate"],
    )
    values = rng.normal(loc=10, scale=2, size=(N_ROWS, N_COLS))
    return pd.DataFrame(values, index=index, columns=columns)


def _make_polars_frame():
    if pl is None:
        return None
    rng = np.random.default_rng(99)
    data = {f"feature_{i:03d}": rng.normal(loc=5, scale=1.5, size=N_ROWS).tolist() for i in range(N_COLS)}
    return pl.DataFrame(data)


app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

status = QLabel(f"QtDataFrameWidget showing large {N_ROWS}x{N_COLS} tables for performance testing.")
table = QtDataFrameWidget(None, _make_pandas_frame())

buttons = QHBoxLayout()

load_pandas_button = QPushButton("Load pandas 500x500")
load_pandas_button.clicked.connect(lambda: table.set_data(_make_pandas_frame()))

load_multiindex_button = QPushButton("Load pandas MultiIndex 500x500")
load_multiindex_button.clicked.connect(lambda: table.set_data(_make_pandas_multiindex()))

load_polars_button = QPushButton("Load polars 500x500")
load_polars_button.setEnabled(pl is not None)
load_polars_button.clicked.connect(lambda: table.set_data(_make_polars_frame()))
if pl is None:
    load_polars_button.setToolTip("Install polars to try the Polars example.")

layout.addWidget(status)
layout.addWidget(table)
buttons.addWidget(load_pandas_button)
buttons.addWidget(load_multiindex_button)
buttons.addWidget(load_polars_button)
layout.addLayout(buttons)

widget.resize(960, 560)
widget.show()

app.exec_()
