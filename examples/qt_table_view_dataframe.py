"""QtDataFrameWidget — coloring demo.

Buttons on the right panel demonstrate the cell-coloring API:
  * color_table()        — auto-detect numeric (diverging) + categorical (tab20)
  * color_numeric()      — diverging RdBu_r centred at 0 for all numeric columns
  * color_categorical()  — unique-value colouring for all text columns
  * clear_colors()       — remove all colouring

Right-clicking a column header exposes per-column colour actions.
Right-clicking a data cell exposes table-wide colour actions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from qtpy.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qtextra.config import THEMES
from qtextra.widgets.qt_table_view_dataframe import QtDataFrameWidget

try:
    import polars as pl
except ImportError:
    pl = None

N_ROWS = 500
N_COLS = 500

# ---------------------------------------------------------------------------
# Data factories
# ---------------------------------------------------------------------------


def _make_pandas_frame() -> pd.DataFrame:
    """Large all-numeric DataFrame for performance testing."""
    rng = np.random.default_rng(42)
    columns = [f"feature_{i:03d}" for i in range(N_COLS)]
    index = [f"sample_{i:03d}" for i in range(N_ROWS)]
    values = rng.normal(loc=10, scale=2, size=(N_ROWS, N_COLS))
    return pd.DataFrame(values, index=index, columns=columns)


def _make_pandas_multiindex() -> pd.DataFrame:
    """Large numeric DataFrame with MultiIndex on both axes."""
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


def _make_mixed_frame() -> pd.DataFrame:
    """Small mixed DataFrame — numeric + categorical — ideal for colour demos."""
    rng = np.random.default_rng(7)
    n = 40
    categories = ["alpha", "beta", "gamma", "delta"]
    statuses = ["active", "inactive", "pending"]
    return pd.DataFrame(
        {
            "score": rng.normal(0, 1, n).round(3),  # numeric, diverging around 0
            "value": rng.uniform(-50, 50, n).round(1),  # numeric, diverging around 0
            "count": rng.integers(0, 200, n).astype(float),  # numeric, sequential
            "ratio": rng.uniform(0, 1, n).round(4),  # numeric, sequential
            "category": rng.choice(categories, n),  # categorical
            "status": rng.choice(statuses, n),  # categorical
            "label": [f"item_{i:03d}" for i in range(n)],  # categorical (all unique)
        }
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = QApplication([])

root = QWidget()
THEMES.apply(root)
root_layout = QHBoxLayout(root)

# --- Table ------------------------------------------------------------------
table = QtDataFrameWidget(None, _make_mixed_frame())
root_layout.addWidget(table, stretch=1)

# --- Control panel ----------------------------------------------------------
panel = QWidget()
panel_layout = QVBoxLayout(panel)
panel_layout.setContentsMargins(4, 4, 4, 4)
panel.setFixedWidth(260)
root_layout.addWidget(panel)

# Load section
load_group = QGroupBox("Load data")
load_layout = QVBoxLayout(load_group)
panel_layout.addWidget(load_group)


def _btn(label: str, slot, *, enabled: bool = True) -> QPushButton:
    b = QPushButton(label)
    b.setEnabled(enabled)
    b.clicked.connect(slot)
    return b


load_layout.addWidget(_btn("Mixed (40 rows, coloring demo)", lambda: table.set_data(_make_mixed_frame())))
load_layout.addWidget(_btn("pandas 500x500 (numeric)", lambda: table.set_data(_make_pandas_frame())))
load_layout.addWidget(_btn("pandas MultiIndex 500x500", lambda: table.set_data(_make_pandas_multiindex())))
load_layout.addWidget(_btn("polars 500x500", lambda: table.set_data(_make_polars_frame()), enabled=pl is not None))

# Coloring section
color_group = QGroupBox("Cell coloring")
color_layout = QVBoxLayout(color_group)
panel_layout.addWidget(color_group)

color_layout.addWidget(QLabel("Entire table:"))
color_layout.addWidget(
    _btn(
        "Color table (auto-detect)",
        lambda: table.color_table(),
    )
)
color_layout.addWidget(
    _btn(
        "Color numeric (diverging, center=0)",
        lambda: table.color_numeric(vcenter=0.0),
    )
)
color_layout.addWidget(
    _btn(
        "Color numeric (sequential, viridis)",
        lambda: table.color_numeric(colormap="viridis", vcenter=None),
    )
)
color_layout.addWidget(
    _btn(
        "Color categorical (tab20)",
        lambda: table.color_categorical(),
    )
)
color_layout.addWidget(
    _btn(
        "Clear all colors",
        lambda: table.clear_colors(),
    )
)

color_layout.addWidget(QLabel("Single column by name:"))
color_layout.addWidget(
    _btn(
        "color_numeric('score', vcenter=0)",
        lambda: table.color_numeric("score", vcenter=0.0),
    )
)
color_layout.addWidget(
    _btn(
        "color_numeric('count', sequential)",
        lambda: table.color_numeric("count", colormap="Blues", vcenter=None),
    )
)
color_layout.addWidget(
    _btn(
        "color_categorical('category')",
        lambda: table.color_categorical("category"),
    )
)
color_layout.addWidget(
    _btn(
        "clear_colors('score')",
        lambda: table.clear_colors("score"),
    )
)

panel_layout.addStretch()
panel_layout.addWidget(QLabel("Tip: right-click a column header\nor a data cell for more options."))

root.resize(1200, 620)
root.show()

app.exec_()
