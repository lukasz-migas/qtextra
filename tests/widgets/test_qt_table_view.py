"""Tests for QtCheckableTableView and TableConfig."""

from __future__ import annotations

import pytest

from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_table_view_check import (
    MultiColumnSingleValueProxyModel,
    QtCheckableItemModel,
    QtCheckableTableView,
)


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def table(qtbot) -> QtCheckableTableView:
    w = QtCheckableTableView(None)
    qtbot.addWidget(w)
    return w


@pytest.fixture
def populated_table(qtbot) -> QtCheckableTableView:
    """Table with 2 columns (Name, Value) sorted ascending by Name."""
    from qtpy.QtCore import Qt

    w = QtCheckableTableView(None)
    qtbot.addWidget(w)
    config = TableConfig().add("Name", "name").add("Value", "value")
    w.setup_model_from_config(config)
    w.add_data([["Alice", 1], ["Bob", 2], ["Carol", 3]])
    # ensure deterministic ascending order for tests
    w.model().sort(0, Qt.SortOrder.AscendingOrder)
    return w


# ── TableConfig ───────────────────────────────────────────────────────────────


class TestTableConfig:
    def test_add_columns(self):
        cfg = TableConfig().add("Col A", "a").add("Col B", "b")
        assert cfg.n_columns == 2
        assert cfg.header == ["Col A", "Col B"]

    def test_find_col_id_by_name(self):
        cfg = TableConfig().add("Alpha", "alpha").add("Beta", "beta")
        assert cfg.find_col_id("Alpha") == 0
        assert cfg.find_col_id("alpha") == 0  # also matches by tag
        assert cfg.find_col_id("Beta") == 1
        assert cfg.find_col_id("missing") == -1

    def test_get_column(self):
        cfg = TableConfig().add("X", "x_tag")
        col = cfg.get_column(0)
        assert col is not None
        assert col["name"] == "X"
        assert col["tag"] == "x_tag"

    def test_hidden_columns(self):
        cfg = TableConfig().add("Visible", "v").add("Hidden", "h", hidden=True)
        assert cfg.hidden_columns == [1]

    def test_update_attribute_by_name(self):
        cfg = TableConfig().add("MyCol", "my_tag")
        cfg.update_attribute("MyCol", "width", 200)
        assert cfg.get_column(0)["width"] == 200

    def test_update_attribute_by_tag(self):
        cfg = TableConfig().add("MyCol", "my_tag")
        cfg.update_attribute("my_tag", "width", 150)
        assert cfg.get_column(0)["width"] == 150

    def test_update_attribute_unknown_name_does_nothing(self):
        cfg = TableConfig().add("MyCol", "my_tag")
        cfg.update_attribute("nonexistent", "width", 999)
        assert cfg.get_column(0)["width"] == 0  # default

    def test_resizable_stored_correctly(self):
        cfg = TableConfig().add("Col", "c", resizable=True)
        col = cfg.get_column(0)
        assert "resizable" in col
        assert col["resizable"] is True

    def test_color_columns(self):
        cfg = TableConfig().add("Color", "color", is_color=True)
        assert 0 in cfg.color_columns

    def test_no_sort_columns(self):
        cfg = TableConfig().add("Static", "s", no_sort=True)
        assert 0 in cfg.no_sort_columns

    def test_bool_dtype_sets_sizing_to_contents(self):
        cfg = TableConfig().add("Flag", "flag", dtype="bool")
        assert cfg.get_column(0)["sizing"] == "contents"

    def test_icon_columns(self):
        cfg = TableConfig().add("Icon", "icon", dtype="icon")
        assert 0 in cfg.icon_columns

    def test_column_iter(self):
        cfg = TableConfig().add("A", "a").add("B", "b")
        pairs = list(cfg.column_iter())
        assert len(pairs) == 2
        assert pairs[0][0] == 0
        assert pairs[1][0] == 1

    def test_get_selected_columns(self):
        cfg = TableConfig().add("Sel", "s", selectable=True).add("NoSel", "n", selectable=False)
        assert cfg.get_selected_columns() == [0]

    def test_get_selectable_columns(self):
        cfg = TableConfig().add("A", "a", selectable=True).add("B", "b", selectable=False)
        assert cfg.get_selectable_columns() == [0]

    def test_to_columns_excludes_check(self):
        cfg = TableConfig().add("", "check").add("Name", "name")
        assert cfg.to_columns(include_check=False) == ["Name"]
        assert cfg.to_columns(include_check=True) == ["", "Name"]


# ── QtCheckableItemModel ──────────────────────────────────────────────────────


class TestModel:
    def test_row_col_count(self):
        model = QtCheckableItemModel(None, data=[["a", "b"], ["c", "d"]], header=["C1", "C2"])
        assert model.rowCount() == 2
        assert model.columnCount() == 2

    def test_empty_model(self):
        model = QtCheckableItemModel(None, data=[], header=[])
        assert model.rowCount() == 0
        assert model.columnCount() == 0

    def test_add_data(self, qtbot):
        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("A", "a").add("B", "b")
        w.setup_model_from_config(cfg)
        w.model().add_data([["x", "y"]])
        assert w.model().rowCount() == 1

    def test_reset_data(self, qtbot):
        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("A", "a")
        w.setup_model_from_config(cfg)
        w.add_data([["x"], ["y"]])
        w.reset_data()
        assert w.n_rows == 0

    def test_remove_row(self, qtbot):
        from qtpy.QtCore import Qt

        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("A", "a")
        w.setup_model_from_config(cfg)
        w.add_data([["x"], ["y"], ["z"]])
        # sort ascending so order is predictable: x=0, y=1, z=2
        w.model().sort(0, Qt.SortOrder.AscendingOrder)
        w.remove_row(1)  # remove "y"
        assert w.n_rows == 2
        assert set(w.get_col_data(0)) == {"x", "z"}

    def test_get_row_id(self, qtbot, populated_table):
        # After ascending sort: Alice=0, Bob=1, Carol=2
        alice_idx = populated_table.get_row_id(0, "Alice")
        bob_idx = populated_table.get_row_id(0, "Bob")
        carol_idx = populated_table.get_row_id(0, "Carol")
        assert alice_idx < bob_idx < carol_idx
        assert populated_table.get_row_id(0, "Nobody") == -1

    def test_get_row_id_for_values(self, qtbot, populated_table):
        # After ascending sort: Alice=row0, Bob=row1, Carol=row2
        col_data = populated_table.get_col_data(0)
        alice_row = col_data.index("Alice")
        carol_row = col_data.index("Carol")
        bob_row = col_data.index("Bob")

        assert populated_table.model().get_row_id_for_values((0, "Bob")) == bob_row
        assert populated_table.model().get_row_id_for_values((0, "Carol"), (1, 3)) == carol_row
        assert populated_table.model().get_row_id_for_values((0, "Alice"), (1, 99)) == -1

    def test_sort(self, qtbot, populated_table):
        from qtpy.QtCore import Qt

        populated_table.model().sort(0, Qt.SortOrder.DescendingOrder)
        assert populated_table.get_col_data(0) == ["Carol", "Bob", "Alice"]

    def test_n_checked_unchecked(self, qtbot):
        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("", "check").add("Name", "name")
        w.setup_model_from_config(cfg)
        w.add_data([[True, "Alice"], [False, "Bob"], [True, "Carol"]])
        assert w.model().n_checked == 2
        assert w.model().n_unchecked == 1

    def test_check_uncheck_all(self, qtbot):
        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("", "check").add("Name", "name")
        w.setup_model_from_config(cfg)
        w.add_data([[False, "Alice"], [False, "Bob"]])
        w.check_all_rows()
        assert w.get_all_checked() == [0, 1]
        w.uncheck_all_rows()
        assert w.get_all_unchecked() == [0, 1]


# ── QtCheckableTableView ──────────────────────────────────────────────────────


class TestTableView:
    def test_init_empty(self, table):
        assert table.n_rows == 0
        assert table.n_cols == 0

    def test_setup_and_add_rows(self, table):
        cfg = TableConfig().add("Test", "test").add("Test2", "test2")
        table.setup_model_from_config(cfg)
        table.add_row(["Test", "Test2"])
        assert table.n_cols == 2
        assert table.n_rows == 1
        table.add_data([["Test", "Test2"]])
        assert table.n_rows == 2

    def test_get_value(self, table):
        cfg = TableConfig().add("Test", "test").add("Test2", "test2")
        table.setup_model_from_config(cfg)
        table.add_row(["Hello", "World"])
        assert table.get_value(0, 0) == "Hello"
        assert table.get_value(1, 0) == "World"

    def test_get_col_data(self, populated_table):
        # ascending sort: Alice < Bob < Carol
        assert populated_table.get_col_data(0) == ["Alice", "Bob", "Carol"]

    def test_get_row_data(self, populated_table):
        # first row after ascending sort is Alice
        row = populated_table.get_row_data(0)
        assert row[0] == "Alice"
        assert row[1] == 1

    def test_get_col_data_boundary(self, populated_table):
        # n_cols == 2, index 2 is out of bounds — should return raw list, not crash
        result = populated_table.get_col_data(2)
        assert isinstance(result, list)

    def test_set_value(self, populated_table):
        # Column 0 is always checkable (bool); use column 1 for string/int values
        populated_table.set_value(1, 0, 99)
        assert populated_table.get_value(1, 0) == 99

    def test_update_column(self, populated_table):
        populated_table.update_column(1, [10, 20, 30])
        assert populated_table.get_col_data(1) == [10, 20, 30]

    def test_find_index_of(self, populated_table):
        bob_idx = populated_table.find_index_of(0, "Bob")
        assert bob_idx >= 0
        assert populated_table.find_index_of(0, "Nobody") == -1

    def test_find_indices_of(self, populated_table):
        populated_table.add_data([["Alice", 4]])
        indices = populated_table.find_indices_of(0, "Alice")
        assert len(indices) == 2

    def test_remove_rows(self, populated_table):
        # ascending order: Alice=0, Bob=1, Carol=2 — remove first and last
        populated_table.remove_rows([0, 2])
        assert populated_table.n_rows == 1
        assert populated_table.get_value(0, 0) == "Bob"

    def test_update_values(self, populated_table):
        # col 0 is always checkable — update col 1 (Value) for non-bool test
        populated_table.update_values(0, {1: 99}, match_to_sort=False)
        assert populated_table.get_value(1, 0) == 99

    def test_get_data(self, populated_table):
        data = populated_table.get_data()
        assert len(data) == 3
        names = {row[0] for row in data}
        assert names == {"Alice", "Bob", "Carol"}


# ── Filter proxy models ────────────────────────────────────────────────────────


class TestFilterProxy:
    def test_filter_single_value(self, qtbot):
        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("Name", "name").add("City", "city")
        w.setup_model_from_config(cfg)
        w.add_data([["Alice", "Berlin"], ["Bob", "Paris"], ["Carol", "Berlin"]])

        proxy = MultiColumnSingleValueProxyModel()
        proxy.setSourceModel(w.model())
        proxy.setFilterByColumn("berlin", 1)
        assert proxy.rowCount() == 2

    def test_filter_cleared_when_empty_string(self, qtbot):
        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("Name", "name")
        w.setup_model_from_config(cfg)
        w.add_data([["Alice"], ["Bob"]])

        proxy = MultiColumnSingleValueProxyModel()
        proxy.setSourceModel(w.model())
        proxy.setFilterByColumn("alice", 0)
        assert proxy.rowCount() == 1
        proxy.setFilterByColumn("", 0)
        assert proxy.rowCount() == 2

    def test_filter_no_spurious_readd_on_empty(self, qtbot):
        """Regression: clearing a filter must not re-add an empty string entry."""
        w = QtCheckableTableView(None)
        qtbot.addWidget(w)
        cfg = TableConfig().add("Name", "name")
        w.setup_model_from_config(cfg)
        w.add_data([["Alice"], ["Bob"]])

        proxy = MultiColumnSingleValueProxyModel()
        proxy.setSourceModel(w.model())
        proxy.setFilterByColumn("alice", 0)
        proxy.setFilterByColumn("", 0)
        # After clearing, dict must not contain the column key
        assert 0 not in proxy.filters_by_text
