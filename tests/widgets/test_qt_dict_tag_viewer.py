"""Tests for the dict tag viewer widget."""

from __future__ import annotations

from qtpy.QtCore import Qt

from qtextra.widgets.qt_dict_tag_viewer import QtDictTagViewer


def test_qt_dict_tag_viewer_exports_typed_dict(qtbot):
    widget = QtDictTagViewer()
    qtbot.addWidget(widget)

    changed = []
    widget.evt_items_changed.connect(changed.append)
    widget.set_items({"alpha": 1, "beta": 2.5, "gamma": None, "delta": "x"})

    assert widget.export_dict() == {"alpha": 1, "beta": 2.5, "gamma": None, "delta": "x"}
    assert changed[-1] == widget.export_dict()
    assert widget.table.rowCount() == 4


def test_qt_dict_tag_viewer_search_filters_rows(qtbot):
    widget = QtDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items({"alpha": 1, "beta": 2, "gamma": 3})

    widget.search_edit.setText("be")

    assert widget.table.isRowHidden(0) is True
    assert widget.table.isRowHidden(1) is False
    assert widget.table.isRowHidden(2) is True


def test_qt_dict_tag_viewer_sorts_by_key_and_value(qtbot):
    widget = QtDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items({"beta": 2, "alpha": 1})

    widget._on_sort_requested(0, Qt.SortOrder.AscendingOrder)
    assert widget.table.item(0, 0).text() == "alpha"

    widget._on_sort_requested(1, Qt.SortOrder.DescendingOrder)
    assert widget.table.item(0, 0).text() == "beta"


def test_qt_dict_tag_viewer_clear_search_preserves_sorted_order(qtbot):
    widget = QtDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items({"beta": 2, "alpha": 1, "gamma": 3})

    widget.search_edit.setText("be")
    widget._on_sort_requested(0, Qt.SortOrder.DescendingOrder)
    widget.search_edit.clear()

    assert [widget.table.item(row, 0).text() for row in range(widget.table.rowCount())] == [
        "gamma",
        "beta",
        "alpha",
    ]
    assert all(not widget.table.isRowHidden(row) for row in range(widget.table.rowCount()))


def test_qt_dict_tag_viewer_get_value_and_clear(qtbot):
    widget = QtDictTagViewer()
    qtbot.addWidget(widget)
    widget.set_items({"alpha": 1})

    assert widget.has_item("alpha") is True
    assert widget.get_value("ALPHA") == 1

    widget.clear_items()
    assert widget.export_dict() == {}
