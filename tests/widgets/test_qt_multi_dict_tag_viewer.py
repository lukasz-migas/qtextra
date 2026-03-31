"""Tests for the multi dict tag viewer widget."""

from __future__ import annotations

from qtpy.QtCore import Qt

from qtextra.widgets.qt_multi_dict_tag_viewer import QtMultiDictTagViewer


def test_qt_multi_dict_tag_viewer_exports_nested_dicts(qtbot):
    widget = QtMultiDictTagViewer()
    qtbot.addWidget(widget)

    changed = []
    widget.evt_items_changed.connect(changed.append)
    widget.set_items(
        {
            "sample_a": {"alpha": 1, "beta": "x"},
            "sample_b": {"alpha": 2, "gamma": None},
        },
    )

    assert widget.export_dicts() == {
        "sample_a": {"alpha": 1, "beta": "x"},
        "sample_b": {"alpha": 2, "gamma": None},
    }
    assert changed[-1] == widget.export_dicts()
    assert widget.key_table.columnCount() == 1
    assert widget.table.columnCount() == 2


def test_qt_multi_dict_tag_viewer_search_filters_rows(qtbot):
    widget = QtMultiDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"alpha": 1, "beta": 2},
            "sample_b": {"alpha": 3, "gamma": 4},
        },
    )

    widget.search_edit.setText("gam")

    assert widget.table.isRowHidden(0) is True
    assert widget.table.isRowHidden(1) is True
    assert widget.table.isRowHidden(2) is False


def test_qt_multi_dict_tag_viewer_sorts_by_key_and_sample(qtbot):
    widget = QtMultiDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"beta": 2, "alpha": 1},
            "sample_b": {"beta": 4, "alpha": 3},
        },
    )

    widget._on_key_sort_requested(0, Qt.SortOrder.AscendingOrder)
    assert widget.key_table.item(0, 0).text() == "alpha"

    widget._on_sample_sort_requested(0, Qt.SortOrder.DescendingOrder)
    assert widget.key_table.item(0, 0).text() == "beta"


def test_qt_multi_dict_tag_viewer_clear_search_preserves_sorted_order(qtbot):
    widget = QtMultiDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"beta": 2, "alpha": 1, "gamma": 3},
            "sample_b": {"beta": 4, "alpha": 3, "gamma": 5},
        },
    )

    widget.search_edit.setText("be")
    widget._on_key_sort_requested(0, Qt.SortOrder.DescendingOrder)
    widget.search_edit.clear()

    assert [widget.key_table.item(row, 0).text() for row in range(widget.key_table.rowCount())] == [
        "gamma",
        "beta",
        "alpha",
    ]
    assert all(not widget.key_table.isRowHidden(row) for row in range(widget.key_table.rowCount()))


def test_qt_multi_dict_tag_viewer_syncs_selection_and_gets_value(qtbot):
    widget = QtMultiDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"alpha": 1},
            "sample_b": {"alpha": 2},
        },
    )

    widget.table.selectRow(0)
    assert widget.key_table.currentRow() == 0
    assert widget.get_value("alpha", "sample_b") == 2

    widget.clear_items()
    assert widget.export_dicts() == {"sample_a": {}, "sample_b": {}}
