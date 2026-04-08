"""Tests for list widgets backed by custom row widgets."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from qtpy.QtWidgets import QLabel

from qtextra.widgets.qt_list_widget import QtListItem, QtListScrollWidget, QtListWidget


@dataclass
class DummyModel:
    name: str
    unique_id: str


class DummyItemWidget(QtListItem):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.name_label = QLabel(self)
        self._set_from_model()

    def _set_from_model(self, _=None) -> None:
        self.name_label.setText(self.item_model.name)


class DummyListWidget(QtListWidget):
    def _make_widget(self, item):
        return DummyItemWidget(item, self)

    def _check_existing(self, item_model: DummyModel) -> bool:
        return self.get_item_for_item_model(item_model) is not None

    def _get_search_terms(self, item_model: DummyModel) -> list[str]:
        return [item_model.name]


class DummyScrollWidget(QtListScrollWidget):
    def _make_widget(self, item_model: DummyModel):
        return DummyItemWidget(item_model, self.widget())

    def _check_existing(self, item_model: DummyModel) -> bool:
        return item_model.unique_id in self.widgets

    def _get_search_terms(self, item_model: DummyModel) -> list[str]:
        return [item_model.name]


@pytest.fixture
def list_widget(qtbot):
    widget = DummyListWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def scroll_widget(qtbot):
    widget = DummyScrollWidget()
    qtbot.addWidget(widget)
    return widget


def test_qt_list_widget_append_move_select_and_remove(list_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")
    gamma = DummyModel(name="Gamma", unique_id="c")

    list_widget.append_item(alpha)
    list_widget.append_item(beta)
    list_widget.append_item(gamma)

    assert [model.name for model in list_widget.model_iter()] == ["Alpha", "Beta", "Gamma"]

    list_widget.select_by_index(1)
    assert list_widget.currentItem().item_model is beta

    list_widget.move_item(0, 2)
    assert [model.name for model in list_widget.model_iter()] == ["Beta", "Gamma", "Alpha"]
    assert list_widget.get_widget_for_hash_id("Alpha").item_model is alpha

    list_widget.remove_by_item_model(beta)
    assert [model.name for model in list_widget.model_iter()] == ["Gamma", "Alpha"]
    assert list_widget.count() == 2


def test_qt_list_widget_insert_emits_added_signal(list_widget):
    seen = []
    list_widget.evt_added.connect(seen.append)

    alpha = DummyModel(name="Alpha", unique_id="a")
    list_widget.insert_item(alpha, index=0)

    assert seen == [alpha]


def test_qt_list_scroll_widget_iteration_matches_visual_order(scroll_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")
    gamma = DummyModel(name="Gamma", unique_id="c")

    scroll_widget.append_item(alpha)
    scroll_widget.append_item(beta)
    scroll_widget.append_item(gamma)

    assert [widget.item_model.name for widget in scroll_widget.widget_iter()] == ["Gamma", "Beta", "Alpha"]
    assert [model.name for model in scroll_widget.model_iter()] == ["Gamma", "Beta", "Alpha"]
    assert scroll_widget.get_item_for_index(0) is gamma
    assert scroll_widget.get_widget_for_hash_id("Beta").item_model is beta


def test_qt_list_scroll_widget_remove_updates_lookup(scroll_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")

    scroll_widget.append_item(alpha)
    scroll_widget.append_item(beta)
    scroll_widget.remove_by_item_model(beta)

    assert [model.name for model in scroll_widget.model_iter()] == ["Alpha"]
    assert scroll_widget.get_widget_for_hash_id("Beta") is None


def test_qt_list_scroll_widget_count_returns_total(scroll_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")

    scroll_widget.append_item(alpha)
    scroll_widget.append_item(beta)
    assert scroll_widget.count() == 2


def test_qt_list_scroll_widget_n_visible_after_filter(scroll_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")
    gamma = DummyModel(name="Gamma", unique_id="c")

    scroll_widget.append_item(alpha)
    scroll_widget.append_item(beta)
    scroll_widget.append_item(gamma)

    visible = scroll_widget.filter_by_text("al")
    assert visible == 1
    assert scroll_widget.n_visible == 1
    assert scroll_widget.count() == 3  # total unchanged

    # empty text restores all
    visible = scroll_widget.filter_by_text("")
    assert visible == 3
    assert scroll_widget.n_visible == 3


def test_qt_list_widget_filter_by_text(list_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")
    gamma = DummyModel(name="Gamma", unique_id="c")

    list_widget.append_item(alpha)
    list_widget.append_item(beta)
    list_widget.append_item(gamma)

    # "al" matches Alpha only (case-insensitive: "alpha" contains "al", "beta"/"gamma" do not)
    visible = list_widget.filter_by_text("al")
    assert visible == 1
    assert list_widget.count() == 3  # total unchanged

    # empty text restores all
    visible = list_widget.filter_by_text("")
    assert visible == 3


def test_qt_list_scroll_widget_reset_data(scroll_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")

    cleared = []
    scroll_widget.evt_cleared.connect(lambda: cleared.append(True))

    scroll_widget.append_item(alpha)
    scroll_widget.append_item(beta)
    scroll_widget.reset_data()

    assert scroll_widget.count() == 0
    assert cleared == [True]


# ------------------------------------------------------------------
# New behaviour: _get_search_terms / set_filter_text / apply_filter
# ------------------------------------------------------------------


def test_list_widget_apply_filter_via_set_filter_text(list_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")
    gamma = DummyModel(name="Gamma", unique_id="c")

    list_widget.append_item(alpha)
    list_widget.append_item(beta)
    list_widget.append_item(gamma)

    # "al" matches only "Alpha"
    list_widget.set_filter_text("al")
    assert list_widget._filter_text == "al"
    assert [m.name for m in list_widget.model_iter()] == ["Alpha"]
    assert [m.name for m in list_widget.all_model_iter()] == ["Alpha", "Beta", "Gamma"]

    # clear filter restores all
    list_widget.set_filter_text("")
    assert [m.name for m in list_widget.model_iter()] == ["Alpha", "Beta", "Gamma"]


def test_scroll_widget_apply_filter_via_set_filter_text(scroll_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")
    gamma = DummyModel(name="Gamma", unique_id="c")

    scroll_widget.append_item(alpha)
    scroll_widget.append_item(beta)
    scroll_widget.append_item(gamma)

    scroll_widget.set_filter_text("et")  # matches "Beta" only
    assert scroll_widget._filter_text == "et"
    assert [m.name for m in scroll_widget.model_iter()] == ["Beta"]
    assert scroll_widget.n_visible == 1

    # all_model_iter ignores visibility
    assert {m.name for m in scroll_widget.all_model_iter()} == {"Alpha", "Beta", "Gamma"}

    scroll_widget.set_filter_text("")
    assert scroll_widget.n_visible == 3


def test_list_widget_iter_respects_visibility(list_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")

    list_widget.append_item(alpha)
    list_widget.append_item(beta)

    list_widget.set_filter_text("al")  # hide Beta

    assert list(list_widget.widget_iter()) == [list_widget.get_widget_for_hash_id("Alpha")]
    assert list(list_widget.all_widget_iter()) != []
    assert len(list(list_widget.all_widget_iter())) == 2


def test_scroll_widget_iter_respects_visibility(scroll_widget):
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")

    scroll_widget.append_item(alpha)
    scroll_widget.append_item(beta)

    scroll_widget.set_filter_text("al")  # hide Beta

    assert len(list(scroll_widget.widget_iter())) == 1
    assert len(list(scroll_widget.all_widget_iter())) == 2


def test_get_widget_for_hash_id_works_for_hidden_items(list_widget):
    """Lookup helpers must find hidden rows too."""
    alpha = DummyModel(name="Alpha", unique_id="a")
    beta = DummyModel(name="Beta", unique_id="b")

    list_widget.append_item(alpha)
    list_widget.append_item(beta)

    list_widget.set_filter_text("al")  # hides Beta

    assert list_widget.get_widget_for_hash_id("Beta") is not None
    assert list_widget.get_widget_for_hash_id("Alpha") is not None
