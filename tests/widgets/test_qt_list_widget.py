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


class DummyScrollWidget(QtListScrollWidget):
    def _make_widget(self, item_model: DummyModel):
        return DummyItemWidget(item_model, self.widget())

    def _check_existing(self, item_model: DummyModel) -> bool:
        return item_model.unique_id in self.widgets


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
