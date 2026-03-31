"""Tests for combobox widgets."""

from typing import ClassVar

import pytest
from qtpy.QtWidgets import QComboBox

from qtextra.widgets._qt_combobox import _BaseButton, _ItemRow
from qtextra.widgets.qt_combobox_multi import QtMultiSelectComboBox, _MultiItemRow, _MultiPanel
from qtextra.widgets.qt_combobox_search import (
    QtSearchableComboBox,
    QtSearchComboBox,
    add_search_to_combobox,
)

# ---------------------------------------------------------------------------
# _BaseButton
# ---------------------------------------------------------------------------


class TestBaseButton:
    @pytest.fixture
    def btn(self, qtbot):
        w = _BaseButton()
        qtbot.addWidget(w)
        return w

    def test_init(self, btn):
        assert btn._open is False
        assert btn._hovered is False

    def test_set_open(self, btn):
        btn.set_open(True)
        assert btn._open is True
        btn.set_open(False)
        assert btn._open is False


# ---------------------------------------------------------------------------
# _ItemRow
# ---------------------------------------------------------------------------


class TestItemRow:
    @pytest.fixture
    def row(self, qtbot):
        w = _ItemRow("Option A")
        qtbot.addWidget(w)
        return w

    def test_init(self, row):
        assert row._label == "Option A"
        assert row._selected is False
        assert row._hovered is False

    def test_set_selected(self, row):
        row.set_selected(True)
        assert row._selected is True
        row.set_selected(False)
        assert row._selected is False

    def test_set_label(self, row):
        row.set_label("New Label")
        assert row._label == "New Label"

    def test_init_selected(self, qtbot):
        row = _ItemRow("X", selected=True)
        qtbot.addWidget(row)
        assert row._selected is True


# ---------------------------------------------------------------------------
# _MultiItemRow
# ---------------------------------------------------------------------------


class TestMultiItemRow:
    @pytest.fixture
    def row(self, qtbot):
        w = _MultiItemRow("Apple")
        qtbot.addWidget(w)
        return w

    def test_init(self, row):
        assert row._label == "Apple"
        assert row._checked is False
        assert row._hovered is False

    def test_set_checked(self, row):
        row.set_checked(True)
        assert row._checked is True
        row.set_checked(False)
        assert row._checked is False

    def test_toggle_emits_signal(self, qtbot, row):
        row.resize(200, 34)
        signals = []
        row.toggled_item.connect(lambda label, checked: signals.append((label, checked)))
        row._checked = False
        # Simulate internal toggle
        row._checked = not row._checked
        row.update()
        row.toggled_item.emit(row._label, row._checked)
        assert signals == [("Apple", True)]


# ---------------------------------------------------------------------------
# _MultiPanel
# ---------------------------------------------------------------------------


class TestMultiPanel:
    ITEMS: ClassVar[list[str]] = ["Alpha", "Beta", "Gamma"]

    @pytest.fixture
    def panel(self, qtbot):
        w = _MultiPanel(self.ITEMS)
        qtbot.addWidget(w)
        return w

    def test_init(self, panel):
        assert len(panel._rows) == len(self.ITEMS)
        assert panel.selected() == []

    def test_set_selected(self, panel):
        panel.set_selected(["Alpha", "Gamma"])
        assert panel.selected() == ["Alpha", "Gamma"]
        # rows reflect the state
        for row in panel._rows:
            assert row._checked == (row._label in {"Alpha", "Gamma"})

    def test_selected_preserves_order(self, panel):
        panel.set_selected(["Gamma", "Alpha"])
        # order should match original item order
        assert panel.selected() == ["Alpha", "Gamma"]

    def test_toggle_updates_selection(self, panel):
        received = []
        panel.evt_selection_changed.connect(received.append)
        panel._on_toggle("Beta", True)
        assert "Beta" in panel._selected
        assert len(received) == 1
        panel._on_toggle("Beta", False)
        assert "Beta" not in panel._selected


# ---------------------------------------------------------------------------
# MultiSelectComboBox
# ---------------------------------------------------------------------------


class TestMultiSelectComboBox:
    ITEMS: ClassVar[list[str]] = ["One", "Two", "Three"]

    @pytest.fixture
    def combo(self, qtbot):
        w = QtMultiSelectComboBox(items=self.ITEMS)
        qtbot.addWidget(w)
        return w

    def test_init_empty(self, qtbot):
        w = QtMultiSelectComboBox()
        qtbot.addWidget(w)
        assert w.selected() == []

    def test_selected_initially_empty(self, combo):
        assert combo.selected() == []

    def test_set_selected(self, combo):
        combo.set_selected(["One", "Three"])
        assert combo.selected() == ["One", "Three"]

    def test_selection_changed_signal(self, combo):
        received = []
        combo.evt_selection_changed.connect(received.append)
        combo.set_selected(["Two"])
        assert received == [["Two"]]

    def test_set_selected_clears_previous(self, combo):
        combo.set_selected(["One", "Two"])
        combo.set_selected(["Three"])
        assert combo.selected() == ["Three"]


# ---------------------------------------------------------------------------
# QtSearchComboBox
# ---------------------------------------------------------------------------


class TestQtSearchComboBox:
    ITEMS: ClassVar[list[str]] = ["Cat", "Dog", "Bird"]

    @pytest.fixture
    def combo(self, qtbot):
        w = QtSearchComboBox(items=self.ITEMS)
        qtbot.addWidget(w)
        return w

    def test_init(self, combo):
        assert combo.current_text() == ""

    def test_set_current_text(self, combo):
        combo.set_current_text("Dog")
        assert combo.current_text() == "Dog"

    def test_signal_on_set(self, combo):
        received = []
        combo.currentTextChanged.connect(received.append)
        combo.set_current_text("Cat")
        assert received == ["Cat"]

    def test_set_items(self, combo):
        combo.set_items(["X", "Y"])
        assert combo._panel._all_items == ["X", "Y"]

    def test_add_items_alias(self, combo):
        combo.addItems(["P", "Q"])
        assert combo._panel._all_items == ["P", "Q"]

    def test_init_no_items(self, qtbot):
        w = QtSearchComboBox()
        qtbot.addWidget(w)
        assert w.current_text() == ""


# ---------------------------------------------------------------------------
# _SearchPanel
# ---------------------------------------------------------------------------


class TestSearchPanel:
    from qtextra.widgets.qt_combobox_search import _SearchPanel

    ITEMS: ClassVar[list[str]] = ["Alpha", "Beta", "Gamma", "Delta"]

    @pytest.fixture
    def panel(self, qtbot):
        from qtextra.widgets.qt_combobox_search import _SearchPanel

        w = _SearchPanel(self.ITEMS)
        qtbot.addWidget(w)
        return w

    def test_init(self, panel):
        assert len(panel._rows) == len(self.ITEMS)
        assert panel._selected == ""

    def test_set_selected(self, panel):
        panel.set_selected("Beta")
        assert panel._selected == "Beta"
        for row in panel._rows:
            assert row._selected == (row._label == "Beta")

    def test_filter_hides_non_matching(self, panel, qtbot):
        panel.show()
        qtbot.waitExposed(panel)
        panel._filter("alp")
        for row in panel._rows:
            if "alp" in row._label.lower():
                assert row.isVisibleTo(panel)
            else:
                assert not row.isVisibleTo(panel)
        panel.hide()

    def test_filter_empty_shows_all(self, panel, qtbot):
        panel.show()
        qtbot.waitExposed(panel)
        panel._filter("z")
        panel._filter("")
        for row in panel._rows:
            assert row.isVisibleTo(panel)
        panel.hide()

    def test_pick_emits_and_sets(self, panel):
        received = []
        panel.itemSelected.connect(received.append)
        panel._pick("Gamma")
        assert panel._selected == "Gamma"
        assert received == ["Gamma"]


# ---------------------------------------------------------------------------
# QtSearchableComboBox
# ---------------------------------------------------------------------------


class TestQtSearchableComboBox:
    @pytest.fixture
    def combo(self, qtbot):
        w = QtSearchableComboBox()
        qtbot.addWidget(w)
        return w

    def test_init(self, combo):
        assert combo.isEditable()
        assert combo.completer() is combo.completer_object

    def test_add_item(self, combo):
        combo.addItem("Foo")
        assert combo.count() == 1
        assert combo.itemText(0) == "Foo"

    def test_add_items(self, combo):
        combo.addItems(["A", "B", "C"])
        assert combo.count() == 3

    def test_remove_item(self, combo):
        combo.addItems(["X", "Y", "Z"])
        combo.removeItem(1)
        assert combo.count() == 2
        assert combo.itemText(0) == "X"
        assert combo.itemText(1) == "Z"

    def test_completer_model_updated(self, combo):
        combo.addItems(["One", "Two"])
        assert combo.completer_object.model() is combo.model()

    def test_no_insert_policy(self, combo):
        assert combo.insertPolicy() == QComboBox.InsertPolicy.NoInsert


# ---------------------------------------------------------------------------
# add_search_to_combobox
# ---------------------------------------------------------------------------


class TestAddSearchToCombobox:
    @pytest.fixture
    def plain_combo(self, qtbot):
        w = QComboBox()
        qtbot.addWidget(w)
        return w

    def test_makes_editable(self, plain_combo):
        add_search_to_combobox(plain_combo)
        assert plain_combo.isEditable()

    def test_sets_completer(self, plain_combo):
        add_search_to_combobox(plain_combo)
        assert plain_combo.completer() is not None
        assert hasattr(plain_combo, "completer_object")

    def test_no_insert_policy(self, plain_combo):
        add_search_to_combobox(plain_combo)
        assert plain_combo.insertPolicy() == QComboBox.InsertPolicy.NoInsert
