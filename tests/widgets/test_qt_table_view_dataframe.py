"""Tests for QtDataFrameWidget."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest
from qtpy.QtCore import Qt

from qtextra.widgets.qt_table_view_dataframe import QtDataFrameWidget


def _expected_data_x(widget: QtDataFrameWidget) -> int:
    return widget.indexHeader.width() + widget.columnHeader.verticalHeader().width()


def _expected_data_y(widget: QtDataFrameWidget) -> int:
    return widget.columnHeader.height() + widget.indexHeader.horizontalHeader().height()


def test_qt_dataframe_widget_renders_pandas_dataframe_and_keeps_headers_aligned(qtbot):
    df = pd.DataFrame(
        {
            "alpha": [1.23456, np.nan],
            "beta": ["x", "y"],
        },
        index=pd.Index(["row_1", "row_2"]),
    )

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.resize(640, 320)
    widget.show()
    qtbot.wait(10)

    model = widget.dataView.model()
    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.data(model.index(0, 0)) == "1.2346"
    assert model.data(model.index(1, 0)) == ""
    assert model.data(model.index(1, 0), role=Qt.ItemDataRole.ToolTipRole) == "NaN"

    assert widget.dataView.geometry().x() == _expected_data_x(widget)
    assert widget.dataView.geometry().y() == _expected_data_y(widget)
    assert widget.cornerSpacer.width() == widget.indexHeader.width()
    assert widget.cornerSpacer.height() == widget.columnHeader.height()


def test_qt_dataframe_widget_handles_pandas_multiindex(qtbot):
    columns = pd.MultiIndex.from_tuples(
        [("A", "x"), ("A", "y"), ("B", "z")],
        names=["upper", "lower"],
    )
    index = pd.MultiIndex.from_tuples(
        [("g1", 1), ("g1", 2), ("g2", 1)],
        names=["group", "n"],
    )
    df = pd.DataFrame([[1, 2, 3], [4, 5, 6], [7, 8, 9]], index=index, columns=columns)

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    assert widget.columnHeader.model().rowCount() == 2
    assert widget.indexHeader.model().columnCount() == 2
    assert widget.columnHeader.model().headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole) == "upper"
    assert widget.indexHeader.model().headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == "group"
    assert widget.columnHeader.columnSpan(0, 0) == 2
    assert widget.indexHeader.rowSpan(0, 0) == 2


def test_qt_dataframe_widget_accepts_polars_dataframe(qtbot):
    pl = pytest.importorskip("polars")

    df = pl.DataFrame(
        {
            "alpha": [1, 2],
            "beta": ["x", "y"],
        },
    )

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    expected = pd.DataFrame(
        {
            "alpha": [1, 2],
            "beta": ["x", "y"],
        },
    )

    assert widget.dataView.model().rowCount() == 2
    assert widget.dataView.model().columnCount() == 2
    assert widget.dataView.model().data(widget.dataView.model().index(0, 1)) == "x"
    pdt.assert_frame_equal(widget.dataView.model().df, expected)


def test_qt_dataframe_widget_realigns_when_switching_single_to_multi_index(qtbot):
    pl = pytest.importorskip("polars")

    widget = QtDataFrameWidget(None, pl.DataFrame({"alpha": [1, 2], "beta": ["x", "y"]}))
    qtbot.addWidget(widget)
    widget.resize(800, 480)
    widget.show()
    qtbot.wait(10)

    columns = pd.MultiIndex.from_tuples([("A", "x"), ("A", "y")], names=["group", "field"])
    index = pd.MultiIndex.from_tuples([("r1", 1), ("r1", 2)], names=["sample", "rep"])
    widget.set_data(pd.DataFrame([[1, 2], [3, 4]], index=index, columns=columns))
    qtbot.wait(10)

    assert widget.dataView.geometry().x() == _expected_data_x(widget)
    assert widget.dataView.geometry().y() == _expected_data_y(widget)
    assert widget.cornerSpacer.width() == widget.indexHeader.width()
    assert widget.cornerSpacer.height() == widget.columnHeader.height()
    assert widget.columnHeader.model().rowCount() == 2
    assert widget.indexHeader.model().columnCount() == 2


def test_qt_dataframe_widget_realigns_when_switching_multi_to_single_index(qtbot):
    columns = pd.MultiIndex.from_tuples([("A", "x"), ("A", "y")], names=["group", "field"])
    index = pd.MultiIndex.from_tuples([("r1", 1), ("r1", 2)], names=["sample", "rep"])
    widget = QtDataFrameWidget(None, pd.DataFrame([[1, 2], [3, 4]], index=index, columns=columns))
    qtbot.addWidget(widget)
    widget.resize(800, 480)
    widget.show()
    qtbot.wait(10)

    widget.set_data(pd.DataFrame({"alpha": [1, 2], "beta": ["x", "y"]}))
    qtbot.wait(10)

    assert widget.dataView.geometry().x() == _expected_data_x(widget)
    assert widget.dataView.geometry().y() == _expected_data_y(widget)
    assert widget.cornerSpacer.width() == widget.indexHeader.width()
    assert widget.cornerSpacer.height() == widget.columnHeader.height()
    assert widget.columnHeader.model().rowCount() == 1
    assert widget.indexHeader.model().columnCount() == 1
