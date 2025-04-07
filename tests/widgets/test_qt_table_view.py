"""Test qt_table_view"""

import pytest

from qtextra.widgets.qt_table_view_check import QtCheckableTableView, TableConfig


@pytest.fixture
def setup_table_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtCheckableTableView:
        """Setup panel"""
        widget = QtCheckableTableView(None)
        qtbot.addWidget(widget)
        return widget

    return _widget


def test_widget_init(qtbot, setup_table_widget):
    widget = setup_table_widget()

    assert widget.n_rows == 0, "Widget should have 0 rows"
    assert widget.n_cols == 0, "Widget should have 0 columns"

    config = TableConfig().add("Test", "test").add("Test2", "test2")
    widget.setup_model_from_config(config)

    widget.add_row(["Test", "Test2"])
    assert widget.n_cols == 2, "Widget should have 2 columns"
    assert widget.n_rows == 1, "Widget should have 1 rows"
    widget.add_data([["Test", "Test2"]])
    assert widget.n_rows == 2, "Widget should have 2 rows"

    assert widget.get_value(0, 0) == "Test"
    assert widget.get_value(1, 0) == "Test2"
    assert widget.get_col_data(0) == ["Test", "Test"]
    assert widget.get_row_data(0) == ["Test", "Test2"]
