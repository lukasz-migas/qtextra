"""Tests for QtArrayTableView."""

from __future__ import annotations

import numpy as np
import pandas as pd
from qtpy.QtCore import QModelIndex, Qt
from qtpy.QtGui import QBrush
from qtpy.QtWidgets import QHeaderView

from qtextra.widgets.qt_table_view_array import BATCH_SIZE, INITIAL_SIZE, QtArrayTableView


def test_qt_array_table_view_accepts_numpy_and_uses_batch_loading(qtbot):
    data = np.arange(240).reshape(120, 2)

    widget = QtArrayTableView()
    qtbot.addWidget(widget)
    widget.set_data(data, fmt="{}")

    model = widget.model()
    assert model.rowCount() == BATCH_SIZE
    assert model.columnCount() == 2
    assert model.canFetchMore()

    model.fetchMore(QModelIndex())
    assert model.rowCount() == 100
    assert model.data(model.index(75, 1), Qt.ItemDataRole.DisplayRole) == "151"


def test_qt_array_table_view_accepts_dataframe_and_sorts(qtbot):
    df = pd.DataFrame({"b": [2, 1, 3], "a": [20, 10, 30]}, index=["r2", "r1", "r3"])

    widget = QtArrayTableView(sortable=True)
    qtbot.addWidget(widget)
    widget.set_data(df, fmt="{}")

    model = widget.model()
    assert model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == "b"
    assert model.headerData(1, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole) == "r1"

    model.sort(0, Qt.SortOrder.AscendingOrder)
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "1"
    assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "10"


def test_qt_array_table_view_updates_formatting_and_header_defaults(qtbot):
    widget = QtArrayTableView()
    qtbot.addWidget(widget)
    widget.set_data(np.array([[1.23456, 2.34567]]), fmt="{:.2f}")

    model = widget.model()
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "1.23"

    widget.set_formatting("{:.1f}")
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "1.2"
    assert widget.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert widget.horizontalHeader().defaultSectionSize() == INITIAL_SIZE


def test_qt_array_table_view_colormap_roles_return_brushes(qtbot):
    widget = QtArrayTableView()
    qtbot.addWidget(widget)
    widget.set_data(np.array([[-1.0, 0.0], [0.5, 1.0]]), fmt="{:.1f}", colormap="viridis", min_val=-1, max_val=1)

    model = widget.model()
    index = model.index(0, 0)

    background = model.data(index, Qt.ItemDataRole.BackgroundRole)
    foreground = model.data(index, Qt.ItemDataRole.ForegroundRole)

    assert isinstance(background, QBrush)
    assert isinstance(foreground, QBrush)
    assert background.color().isValid()
    assert foreground.color().isValid()


def test_qt_array_table_view_reset_data_clears_model(qtbot):
    widget = QtArrayTableView()
    qtbot.addWidget(widget)
    widget.set_data(np.arange(12).reshape(6, 2), fmt="{}")

    widget.reset_data()

    model = widget.model()
    assert model.rowCount() == 0
    assert model.columnCount() == 0
    assert not model.canFetchMore()
