"""Tests for the dict tag editor widget."""

from __future__ import annotations

import pytest
from qtpy.QtGui import QDoubleValidator, QIntValidator

import qtextra.helpers as hp
from qtextra.widgets.qt_dict_tag_editor import QtDictTagEditor


def test_qt_dict_tag_editor_add_and_export(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)

    changed = []
    added = []
    widget.evt_items_changed.connect(changed.append)
    widget.evt_item_added.connect(lambda key, value: added.append((key, value)))

    assert widget.add_item("name", "alpha") is True
    assert widget.add_item("count", 3) is True
    assert widget.add_item("ratio", 1.5) is True
    assert widget.add_item("missing", None) is True

    assert widget.export_dict() == {
        "name": "alpha",
        "count": 3,
        "ratio": 1.5,
        "missing": None,
    }
    assert added[-1] == ("missing", None)
    assert changed[-1] == widget.export_dict()
    assert widget.table.rowCount() == 4
    assert widget.table.item(0, 0).text() == "name"
    assert widget.table.item(0, 1).text() == "alpha"


def test_qt_dict_tag_editor_adds_current_item_with_types(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)

    widget.key_edit.setText("count")
    widget.value_edit.setText("10")
    widget.type_combo.setCurrentText("int")
    assert widget.add_current_item() is True

    widget.key_edit.setText("ratio")
    widget.value_edit.setText("0.25")
    widget.type_combo.setCurrentText("float")
    assert widget.add_current_item() is True

    widget.key_edit.setText("notes")
    widget.type_combo.setCurrentText("None")
    assert widget.add_current_item() is True

    assert widget.export_dict() == {"count": 10, "ratio": 0.25, "notes": None}
    assert widget.key_edit.text() == ""
    assert widget.value_edit.text() == ""
    assert widget.table.item(2, 2).text() == "None"


def test_qt_dict_tag_editor_invalid_numeric_value_is_rejected(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)

    widget.key_edit.setText("count")
    widget.type_combo.setCurrentText("int")
    widget.value_edit.setText("")

    assert widget.add_current_item() is False
    assert widget.export_dict() == {}


def test_qt_dict_tag_editor_duplicate_key_replaces_value(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)

    assert widget.add_item("Alpha", 1) is True
    assert widget.add_item("alpha", 2) is True

    assert widget.export_dict() == {"alpha": 2}
    assert widget.get_value("ALPHA") == 2
    assert widget.table.rowCount() == 1


def test_qt_dict_tag_editor_remove_and_replace_items(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items({"alpha": "one", "beta": 2, "gamma": None})

    removed = []
    widget.evt_item_removed.connect(removed.append)

    assert widget.remove_item("beta") is True
    assert widget.export_dict() == {"alpha": "one", "gamma": None}
    assert removed == ["beta"]

    widget.set_items({"one": 1, "two": 2})
    assert widget.export_dict() == {"one": 1, "two": 2}


def test_qt_dict_tag_editor_preserves_order(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)
    widget.add_items({"first": 1, "second": 2, "third": 3})

    assert list(widget.items()) == ["first", "second", "third"]
    assert widget.has_item("second") is True


def test_qt_dict_tag_editor_search_filters_rows(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items({"alpha": 1, "beta": 2, "gamma": 3})

    widget.search_edit.setText("be")

    assert widget.table.isRowHidden(0) is True
    assert widget.table.isRowHidden(1) is False
    assert widget.table.isRowHidden(2) is True


def test_qt_dict_tag_editor_selecting_row_populates_inputs(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items({"alpha": 1, "beta": None})

    widget.table.selectRow(0)

    assert widget.key_edit.text() == "alpha"
    assert widget.value_edit.text() == "1"
    assert widget.type_combo.currentText() == "int"

    widget.table.selectRow(1)

    assert widget.key_edit.text() == "beta"
    assert widget.value_edit.text() == ""
    assert widget.type_combo.currentText() == "None"
    assert widget.value_edit.isEnabled() is False


def test_qt_dict_tag_editor_type_selection_updates_validator(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)

    widget.type_combo.setCurrentText("int")
    assert isinstance(widget.value_edit.validator(), QIntValidator)

    widget.type_combo.setCurrentText("float")
    assert isinstance(widget.value_edit.validator(), QDoubleValidator)

    widget.type_combo.setCurrentText("None")
    assert widget.value_edit.validator() is None
    assert widget.value_edit.isEnabled() is False


def test_qt_dict_tag_editor_rejects_unsupported_value_type(qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)

    with pytest.raises(TypeError):
        widget.add_item("bad", [])


def test_qt_dict_tag_editor_confirm_clear_items(monkeypatch, qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items({"alpha": 1})

    monkeypatch.setattr(hp, "confirm", lambda *args, **kwargs: True)

    assert widget.confirm_clear_items() is True
    assert widget.export_dict() == {}


def test_qt_dict_tag_editor_confirm_clear_items_cancelled(monkeypatch, qtbot):
    widget = QtDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items({"alpha": 1})

    monkeypatch.setattr(hp, "confirm", lambda *args, **kwargs: False)

    assert widget.confirm_clear_items() is False
    assert widget.export_dict() == {"alpha": 1}
