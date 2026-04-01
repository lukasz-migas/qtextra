"""QtDataFrameWidget."""

from __future__ import annotations

import numpy as np
import pandas as pd
from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_table_view_dataframe import QtDataFrameWidget

try:
    import polars as pl
except ImportError:
    pl = None


def _make_pandas_multiindex() -> pd.DataFrame:
    columns = pd.MultiIndex.from_tuples(
        [("Intensity", "mean"), ("Intensity", "std"), ("Quality", "score")],
        names=["metric", "stat"],
    )
    index = pd.MultiIndex.from_tuples(
        [("sample_a", 1), ("sample_a", 2), ("sample_b", 1), ("sample_b", 2)],
        names=["sample", "replicate"],
    )
    values = np.random.default_rng().normal(loc=10, scale=2, size=(len(index), len(columns)))
    return pd.DataFrame(values, index=index, columns=columns)


def _make_polars_frame():
    if pl is None:
        return None
    return pl.DataFrame(
        {
            "sample": ["sample_a", "sample_b", "sample_c"],
            "area": [101.2, 98.5, 110.1],
            "passed": [True, True, False],
        },
    )


app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

status = QLabel("QtDataFrameWidget displaying a pandas MultiIndex DataFrame.")
table = QtDataFrameWidget(None, _make_pandas_multiindex() if pl is None else _make_polars_frame())

load_pandas_button = QPushButton("Load pandas MultiIndex")
load_pandas_button.clicked.connect(lambda: table.set_data(_make_pandas_multiindex()))

load_polars_button = QPushButton("Load polars DataFrame")
load_polars_button.setEnabled(pl is not None)
load_polars_button.clicked.connect(lambda: table.set_data(_make_polars_frame()))
if pl is None:
    load_polars_button.setToolTip("Install polars to try the Polars example.")

layout.addWidget(status)
layout.addWidget(table)
layout.addWidget(load_pandas_button)
layout.addWidget(load_polars_button)

widget.resize(960, 560)
widget.show()

app.exec_()
