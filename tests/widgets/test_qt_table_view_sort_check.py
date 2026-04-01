"""Tests for proxy-sorted checkable table view."""

from __future__ import annotations

from qtpy.QtCore import Qt

from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_table_view_sort_check import QtProxySortCheckableTableView


def test_proxy_sort_keeps_source_data_unsorted(qtbot):
    w = QtProxySortCheckableTableView(None, config=TableConfig().add("Name", "name").add("Value", "value"))
    qtbot.addWidget(w)
    w.add_data([["Bob", 2], ["Alice", 1], ["Carol", 3]])

    proxy = w.proxy_model()
    assert proxy is not None
    proxy.sort(0, Qt.SortOrder.AscendingOrder)

    assert w.get_col_data(0) == ["Alice", "Bob", "Carol"]
    assert w.model().get_data() == [["Bob", 2], ["Alice", 1], ["Carol", 3]]


def test_proxy_sort_visible_row_updates_map_back_to_source(qtbot):
    w = QtProxySortCheckableTableView(None, config=TableConfig().add("Name", "name").add("Value", "value"))
    qtbot.addWidget(w)
    w.add_data([["Bob", 2], ["Alice", 1], ["Carol", 3]])

    proxy = w.proxy_model()
    assert proxy is not None
    proxy.sort(0, Qt.SortOrder.AscendingOrder)

    w.update_value(0, 1, 99, match_to_sort=False)

    assert w.get_row_data(0) == ["Alice", 99]
    assert w.model().get_data()[1] == ["Alice", 99]


def test_proxy_sort_select_row_maps_source_to_view(qtbot):
    w = QtProxySortCheckableTableView(None, config=TableConfig().add("Name", "name").add("Value", "value"))
    qtbot.addWidget(w)
    w.add_data([["Bob", 2], ["Alice", 1], ["Carol", 3]])

    proxy = w.proxy_model()
    assert proxy is not None
    proxy.sort(0, Qt.SortOrder.AscendingOrder)

    w.select_row(0, match_to_sort=True)

    assert w.currentIndex().row() == 1
