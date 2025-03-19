"""Test qt_table_view"""

import pytest
from qtextra.widgets.qt_table_view_check import QtCheckableTableView


@pytest.fixture
def make_widget(qtbot):
    widget = QtCheckableTableView(None)
    qtbot.addWidget(widget)
    return widget


def test_widget_init(qtbot, make_widget):
    widget = make_widget

    assert widget.n_rows == 0
    assert widget.n_cols == 0
