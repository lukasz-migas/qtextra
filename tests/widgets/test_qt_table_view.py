""" Test qt_table_view"""

# Third-party imports
import pytest

# Local imports
from ionglow._qt.qt_table_view import QtCheckableTableView


@pytest.fixture
def make_widget(qtbot):
    widget = QtCheckableTableView(None)
    qtbot.addWidget(widget)
    return widget


def test_widget_init(qtbot, make_widget):
    widget = make_widget

    assert widget.n_rows == 0
    assert widget.n_cols == 0
