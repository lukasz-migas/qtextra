"""Tests for QtDataFrameWidget."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QGuiApplication

from qtextra.widgets.qt_table_view_dataframe import ColumnVisibilityDialog, QtDataFrameWidget, RowVisibilityDialog


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

    assert widget.dataView.geometry().x() == widget.indexHeader.width()
    assert widget.dataView.geometry().y() == widget.columnHeader.height()
    assert widget.cornerView.width() == widget.indexHeader.width()
    assert widget.cornerView.height() == widget.columnHeader.height()


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

    assert widget.dataView.geometry().x() == widget.indexHeader.width()
    assert widget.dataView.geometry().y() == widget.columnHeader.height()
    assert widget.cornerView.width() == widget.indexHeader.width()
    assert widget.cornerView.height() == widget.columnHeader.height()
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

    assert widget.dataView.geometry().x() == widget.indexHeader.width()
    assert widget.dataView.geometry().y() == widget.columnHeader.height()
    assert widget.cornerView.width() == widget.indexHeader.width()
    assert widget.cornerView.height() == widget.columnHeader.height()
    assert widget.columnHeader.model().rowCount() == 1
    assert widget.indexHeader.model().columnCount() == 1


def test_qt_dataframe_widget_keeps_last_column_aligned_at_max_horizontal_scroll(qtbot):
    df = pd.DataFrame({f"col_{index}": np.arange(5) + index for index in range(12)})

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.resize(360, 220)
    widget.show()
    qtbot.wait(50)

    scrollbar = widget.dataView.horizontalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    qtbot.wait(10)

    last_column = widget.dataView.model().columnCount() - 1
    data_rect = widget.dataView.visualRect(widget.dataView.model().index(0, last_column))
    header_rect = widget.columnHeader.visualRect(widget.columnHeader.model().index(0, last_column))

    assert abs(data_rect.left() - header_rect.left()) <= 1
    assert data_rect.width() == header_rect.width()


def test_qt_dataframe_widget_sorts_rows_and_can_clear_sorting(qtbot):
    df = pd.DataFrame({"b": [2, 1, 3], "a": [20, 10, 30]}, index=["r2", "r1", "r3"])

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.toggle_sort(0)
    assert widget.indexHeader.model().data(widget.indexHeader.model().index(0, 0)) == "r1"
    assert widget.dataView.model().data(widget.dataView.model().index(0, 0)) == "1"
    assert widget.columnHeader.model().data(widget.columnHeader.model().index(0, 0)) == "b ▲"

    widget.toggle_sort(0)
    assert widget.indexHeader.model().data(widget.indexHeader.model().index(0, 0)) == "r3"
    assert widget.dataView.model().data(widget.dataView.model().index(0, 0)) == "3"
    assert widget.columnHeader.model().data(widget.columnHeader.model().index(0, 0)) == "b ▼"

    widget.toggle_sort(0)
    assert widget.indexHeader.model().data(widget.indexHeader.model().index(0, 0)) == "r2"
    assert widget.dataView.model().data(widget.dataView.model().index(0, 0)) == "2"
    assert widget.columnHeader.model().data(widget.columnHeader.model().index(0, 0)) == "b"


def test_qt_dataframe_widget_filters_numeric_ranges_and_blanks(qtbot):
    df = pd.DataFrame({"value": [1.0, 5.0, np.nan, 9.0], "name": ["a", "b", "c", "d"]}, index=list("wxyz"))

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.set_numeric_filter(0, minimum=2.0, maximum=6.0, include_blanks=False)
    assert widget.dataView.model().rowCount() == 1
    assert widget.indexHeader.model().data(widget.indexHeader.model().index(0, 0)) == "x"

    widget.set_numeric_filter(0, minimum=2.0, maximum=6.0, include_blanks=True)
    assert widget.dataView.model().rowCount() == 2
    assert widget.indexHeader.model().data(widget.indexHeader.model().index(1, 0)) == "y"


def test_qt_dataframe_widget_filters_strings_with_current_values(qtbot):
    df = pd.DataFrame(
        {
            "team": ["red", "red", "blue", None],
            "city": ["london", "paris", "paris", "rome"],
        },
        index=["r1", "r2", "r3", "r4"],
    )

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.set_value_filter(1, {"paris"}, include_blanks=False)
    assert widget.proxy_model.distinct_values_for_column(0) == ["blue", "red"]

    widget.set_value_filter(0, {"red"}, include_blanks=False)
    assert widget.dataView.model().rowCount() == 1
    assert widget.indexHeader.model().data(widget.indexHeader.model().index(0, 0)) == "r2"


def test_qt_dataframe_widget_can_clear_all_filters(qtbot):
    df = pd.DataFrame(
        {
            "team": ["red", "red", "blue", None],
            "city": ["london", "paris", "paris", "rome"],
        },
        index=["r1", "r2", "r3", "r4"],
    )

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.set_value_filter(1, {"paris"}, include_blanks=False)
    widget.set_value_filter(0, {"red"}, include_blanks=False)
    assert widget.dataView.model().rowCount() == 1

    widget.clear_filters()

    assert widget.dataView.model().rowCount() == 4
    assert not widget.proxy_model.is_column_filtered(0)
    assert not widget.proxy_model.is_column_filtered(1)


def test_qt_dataframe_widget_hides_and_restores_columns(qtbot):
    df = pd.DataFrame({"alpha": [1, 2], "beta": [3, 4], "gamma": [5, 6]})

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.set_column_visible(1, False)
    assert widget.visible_columns() == [0, 2]
    assert widget.dataView.model().columnCount() == 2
    assert widget.columnHeader.model().data(widget.columnHeader.model().index(0, 1)) == "gamma"

    widget.set_column_visible(1, True)
    assert widget.visible_columns() == [0, 1, 2]
    assert widget.dataView.model().columnCount() == 3


def test_qt_dataframe_widget_hides_and_restores_rows(qtbot):
    df = pd.DataFrame({"alpha": [1, 2, 3], "beta": [4, 5, 6]}, index=["r1", "r2", "r3"])

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.set_row_visible(1, False)
    assert widget.visible_rows() == [0, 2]
    assert widget.dataView.model().rowCount() == 2
    assert widget.indexHeader.model().data(widget.indexHeader.model().index(1, 0)) == "r3"

    widget.set_row_visible(1, True)
    assert widget.visible_rows() == [0, 1, 2]
    assert widget.dataView.model().rowCount() == 3


def test_qt_dataframe_widget_keeps_last_visible_column(qtbot):
    df = pd.DataFrame({"alpha": [1, 2]})

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.set_column_visible(0, False)
    assert widget.visible_columns() == [0]


def test_qt_dataframe_widget_keeps_last_visible_row(qtbot):
    df = pd.DataFrame({"alpha": [1, 2]}, index=["r1", "r2"])

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.set_row_visible(0, False)
    widget.set_row_visible(1, False)
    assert widget.visible_rows() == [1]


def test_qt_dataframe_widget_resets_proxy_state_on_set_data(qtbot):
    df = pd.DataFrame({"alpha": [2, 1], "beta": ["x", "y"]}, index=["r2", "r1"])
    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.toggle_sort(0)
    widget.set_value_filter(1, {"x"}, include_blanks=False)
    widget.set_column_visible(1, False)

    widget.set_data(pd.DataFrame({"left": [1, 2], "right": [3, 4]}))
    qtbot.wait(10)

    assert widget.proxy_model.sort_column is None
    assert widget.dataView.model().rowCount() == 2
    assert widget.visible_columns() == [0, 1]
    assert widget.dataView.geometry().x() == widget.indexHeader.width()
    assert widget.dataView.geometry().y() == widget.columnHeader.height()


def test_column_visibility_dialog_lists_columns_in_bounded_view(qtbot):
    df = pd.DataFrame({f"column_{index}": [index] for index in range(40)})
    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)

    dialog = ColumnVisibilityDialog(widget, widget.proxy_model)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(10)

    assert dialog.columns_list.count() == 40
    assert dialog.checked_columns() == list(range(40))
    assert dialog.height() <= 420


def test_column_visibility_dialog_supports_checking_and_filtering(qtbot):
    df = pd.DataFrame({"alpha": [1], "beta": [2], "gamma": [3]})
    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.set_column_visible(1, False)

    dialog = ColumnVisibilityDialog(widget, widget.proxy_model)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(10)

    dialog._uncheck_all()
    assert dialog.checked_columns() == [0]

    dialog._check_all()
    assert dialog.checked_columns() == [0, 1, 2]

    dialog.visibility_filter.setCurrentText("Hidden columns")
    qtbot.wait(10)
    visible_items = [
        dialog.columns_list.item(row).text()
        for row in range(dialog.columns_list.count())
        if not dialog.columns_list.item(row).isHidden()
    ]
    assert visible_items == ["beta"]

    dialog.visibility_filter.setCurrentText("Visible columns")
    qtbot.wait(10)
    visible_items = [
        dialog.columns_list.item(row).text()
        for row in range(dialog.columns_list.count())
        if not dialog.columns_list.item(row).isHidden()
    ]
    assert visible_items == ["alpha", "gamma"]


def test_row_visibility_dialog_supports_checking_and_filtering(qtbot):
    df = pd.DataFrame({"alpha": [1, 2, 3]}, index=["r1", "r2", "r3"])
    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.set_row_visible(1, False)

    dialog = RowVisibilityDialog(widget, widget.proxy_model)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(10)

    dialog._uncheck_all()
    assert dialog.checked_rows() == [0]

    dialog._check_all()
    assert dialog.checked_rows() == [0, 1, 2]

    dialog.visibility_filter.setCurrentText("Hidden rows")
    qtbot.wait(10)
    visible_items = [
        dialog.rows_list.item(row).text()
        for row in range(dialog.rows_list.count())
        if not dialog.rows_list.item(row).isHidden()
    ]
    assert visible_items == ["r2"]

    dialog.visibility_filter.setCurrentText("Visible rows")
    qtbot.wait(10)
    visible_items = [
        dialog.rows_list.item(row).text()
        for row in range(dialog.rows_list.count())
        if not dialog.rows_list.item(row).isHidden()
    ]
    assert visible_items == ["r1", "r3"]


def test_qt_dataframe_widget_copy_selection_includes_headers_and_index(qtbot):
    df = pd.DataFrame({"alpha": [1, 2], "beta": [3, 4]}, index=["r1", "r2"])

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.dataView.selectRow(0)
    widget.dataView.copy_selection_to_clipboard()

    clipboard_text = QGuiApplication.clipboard().text()
    assert "alpha" in clipboard_text
    assert "beta" in clipboard_text
    assert "r1" in clipboard_text
    assert "1" in clipboard_text
    assert "3" in clipboard_text


def test_qt_dataframe_widget_copy_selected_columns_uses_visible_rows(qtbot):
    df = pd.DataFrame({"alpha": [1, 2], "beta": [3, 4]}, index=["r1", "r2"])

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    widget.dataView.selectColumn(1)
    widget.dataView.copy_selected_columns_to_clipboard()

    clipboard_text = QGuiApplication.clipboard().text()
    assert "beta" in clipboard_text
    assert "alpha" not in clipboard_text
    assert "r1" in clipboard_text
    assert "r2" in clipboard_text


def test_qt_dataframe_widget_drag_select_on_header_does_not_sort(qtbot):
    df = pd.DataFrame({"b": [2, 1, 3], "a": [20, 10, 30]}, index=["r2", "r1", "r3"])

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    first_rect = widget.columnHeader.visualRect(widget.columnHeader.model().index(0, 0))
    second_rect = widget.columnHeader.visualRect(widget.columnHeader.model().index(0, 1))
    start_pos = first_rect.center()
    end_pos = second_rect.center()

    qtbot.mousePress(widget.columnHeader.viewport(), Qt.MouseButton.LeftButton, pos=start_pos)
    qtbot.mouseMove(widget.columnHeader.viewport(), pos=end_pos)
    qtbot.mouseRelease(widget.columnHeader.viewport(), Qt.MouseButton.LeftButton, pos=end_pos)

    assert widget.proxy_model.sort_column is None
    assert widget.dataView.model().data(widget.dataView.model().index(0, 0)) == "2"


def test_qt_dataframe_widget_single_level_headers_do_not_create_single_cell_spans(qtbot):
    df = pd.DataFrame({"alpha": [1, 2], "beta": [3, 4]}, index=["r1", "r2"])

    widget = QtDataFrameWidget(None, df)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    assert widget.columnHeader.columnSpan(0, 0) == 1
    assert widget.columnHeader.columnSpan(0, 1) == 1
    assert widget.indexHeader.rowSpan(0, 0) == 1
    assert widget.indexHeader.rowSpan(1, 0) == 1
