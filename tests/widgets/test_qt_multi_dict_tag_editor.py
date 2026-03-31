"""Tests for the multi dict tag editor widget."""

from __future__ import annotations

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QDoubleValidator, QIntValidator

import qtextra.helpers as hp
from qtextra.widgets.qt_multi_dict_tag_editor import QtMultiDictTagEditor


def test_qt_multi_dict_tag_editor_exports_nested_dicts(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)

    changed = []
    widget.evt_items_changed.connect(changed.append)

    widget.set_items(
        {
            "sample_a": {"alpha": 1, "beta": "x"},
            "sample_b": {"alpha": 2, "gamma": None},
        },
    )

    assert widget.export_dicts() == {
        "sample_a": {"alpha": 1, "beta": "x"},
        "sample_b": {"alpha": 2, "gamma": None},
    }
    assert changed[-1] == widget.export_dicts()
    assert widget.key_table.columnCount() == 2
    assert widget.table.columnCount() == 2
    assert widget.all_samples_button.text() == "Select All"


def test_qt_multi_dict_tag_editor_adds_key_to_all_samples(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a", "sample_b"])
    qtbot.addWidget(widget)

    assert widget.add_key("status", "ready") is True

    assert widget.export_dicts() == {
        "sample_a": {"status": "ready"},
        "sample_b": {"status": "ready"},
    }


def test_qt_multi_dict_tag_editor_adds_key_to_one_sample(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a", "sample_b"])
    qtbot.addWidget(widget)

    assert widget.add_key("status", "ready", target_sample="sample_b") is True

    assert widget.export_dicts() == {
        "sample_a": {},
        "sample_b": {"status": "ready"},
    }


def test_qt_multi_dict_tag_editor_applies_value_to_one_or_all_samples(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"score": 1.0},
            "sample_b": {"score": 2.0},
        },
    )

    assert widget.set_value("score", 3.5, target_sample="sample_a") is True
    assert widget.get_value("score", "sample_a") == 3.5
    assert widget.get_value("score", "sample_b") == 2.0

    assert widget.set_value("score", 4.5) is True
    assert widget.export_dicts() == {
        "sample_a": {"score": 4.5},
        "sample_b": {"score": 4.5},
    }


def test_qt_multi_dict_tag_editor_current_controls_target_selected_sample(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a", "sample_b"])
    qtbot.addWidget(widget)

    widget.key_edit.setText("count")
    widget.value_edit.setText("3")
    widget.type_toggle.value = "int"
    widget.set_target_samples(["sample_b"])
    assert widget.add_current_key() is True

    widget.key_edit.setText("count")
    widget.value_edit.setText("4")
    widget.type_toggle.value = "int"
    widget.set_target_samples(["sample_b"])
    assert widget.apply_current_value() is True

    assert widget.export_dicts() == {
        "sample_a": {},
        "sample_b": {"count": 4},
    }


def test_qt_multi_dict_tag_editor_current_controls_multiple_selected_samples(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a", "sample_b", "sample_c"])
    qtbot.addWidget(widget)

    widget.key_edit.setText("group")
    widget.value_edit.setText("treated")
    widget.type_toggle.value = "str"
    widget.set_target_samples(["sample_a", "sample_b"])
    assert widget.add_current_key() is True

    assert widget.export_dicts() == {
        "sample_a": {"group": "treated"},
        "sample_b": {"group": "treated"},
        "sample_c": {},
    }


def test_qt_multi_dict_tag_editor_all_samples_option_targets_everything(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a", "sample_b"])
    qtbot.addWidget(widget)

    widget.set_target_samples([])
    assert widget.current_target_samples() == ["sample_a", "sample_b"]

    widget.key_edit.setText("status")
    widget.value_edit.setText("done")
    widget.type_toggle.value = "str"
    assert widget.add_current_key() is True

    assert widget.export_dicts() == {
        "sample_a": {"status": "done"},
        "sample_b": {"status": "done"},
    }


def test_qt_multi_dict_tag_editor_select_all_button_selects_all_combo_items(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a", "sample_b", "sample_c"])
    qtbot.addWidget(widget)

    widget.set_target_samples(["sample_a", "sample_b"])
    assert widget.sample_combo.selected() == ["sample_a", "sample_b"]

    widget.all_samples_button.click()
    assert widget.sample_combo.selected() == ["sample_a", "sample_b", "sample_c"]
    assert widget.sample_combo.selected() == ["sample_a", "sample_b", "sample_c"]


def test_qt_multi_dict_tag_editor_empty_combo_selection_targets_none(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a", "sample_b", "sample_c"])
    qtbot.addWidget(widget)

    widget.sample_combo.set_selected([])

    assert widget.current_target_samples() == []
    assert widget.target_summary.text() == "Targets: none"


def test_qt_multi_dict_tag_editor_search_filters_rows(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"alpha": 1, "beta": 2},
            "sample_b": {"alpha": 3, "gamma": 4},
        },
    )

    widget.search_edit.setText("gam")

    assert widget.table.isRowHidden(0) is True
    assert widget.table.isRowHidden(1) is True
    assert widget.table.isRowHidden(2) is False


def test_qt_multi_dict_tag_editor_selection_populates_inputs_for_target(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"alpha": 1},
            "sample_b": {"alpha": 2},
        },
    )

    widget.set_target_samples(["sample_b"])
    widget.table.selectRow(0)

    assert widget.key_edit.text() == "alpha"
    assert widget.current_value_type() == "int"
    assert widget.value_edit.text() == "2"

    widget.set_target_samples(["sample_a", "sample_b"])
    assert widget.value_edit.text() == ""


def test_qt_multi_dict_tag_editor_double_click_targets_clicked_sample(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"alpha": 1},
            "sample_b": {"alpha": 2},
        },
    )

    widget._on_cell_double_clicked(0, 1)

    assert widget.current_target_samples() == ["sample_b"]
    assert widget.key_edit.text() == "alpha"
    assert widget.value_edit.text() == "2"
    assert widget.current_value_type() == "int"


def test_qt_multi_dict_tag_editor_key_and_type_columns_resize_to_contents(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"very_long_key_name": "alpha"},
            "sample_b": {"very_long_key_name": "beta"},
        },
    )

    assert widget.key_table.columnWidth(0) >= 120
    assert widget.key_table.columnWidth(1) >= 88


def test_qt_multi_dict_tag_editor_type_selection_updates_validator(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a"])
    qtbot.addWidget(widget)

    widget.set_current_value_type("int")
    assert isinstance(widget.value_edit.validator(), QIntValidator)

    widget.set_current_value_type("float")
    assert isinstance(widget.value_edit.validator(), QDoubleValidator)

    widget.set_current_value_type("None")
    assert widget.value_edit.validator() is None
    assert widget.value_edit.isEnabled() is False


def test_qt_multi_dict_tag_editor_sorts_by_key(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"beta": 2, "alpha": 1},
            "sample_b": {"beta": 4, "alpha": 3},
        },
    )

    widget._on_key_sort_requested(0, Qt.SortOrder.AscendingOrder)
    assert widget.key_table.item(0, 0).text() == "alpha"

    widget._on_key_sort_requested(0, Qt.SortOrder.DescendingOrder)
    assert widget.key_table.item(0, 0).text() == "beta"


def test_qt_multi_dict_tag_editor_remove_selected_key(qtbot):
    widget = QtMultiDictTagEditor()
    qtbot.addWidget(widget)
    widget.set_items(
        {
            "sample_a": {"alpha": 1},
            "sample_b": {"alpha": 2, "beta": 3},
        },
    )

    widget.table.selectRow(0)
    assert widget.remove_selected_key() is True

    assert widget.export_dicts() == {
        "sample_a": {},
        "sample_b": {"beta": 3},
    }


def test_qt_multi_dict_tag_editor_rejects_unsupported_value_type(qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a"])
    qtbot.addWidget(widget)

    with pytest.raises(TypeError):
        widget.add_key("bad", [])


def test_qt_multi_dict_tag_editor_confirm_clear_items(monkeypatch, qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a"])
    qtbot.addWidget(widget)
    widget.set_items({"sample_a": {"alpha": 1}})

    monkeypatch.setattr(hp, "confirm", lambda *args, **kwargs: True)

    assert widget.confirm_clear_items() is True
    assert widget.export_dicts() == {"sample_a": {}}


def test_qt_multi_dict_tag_editor_confirm_clear_items_cancelled(monkeypatch, qtbot):
    widget = QtMultiDictTagEditor(samples=["sample_a"])
    qtbot.addWidget(widget)
    widget.set_items({"sample_a": {"alpha": 1}})

    monkeypatch.setattr(hp, "confirm", lambda *args, **kwargs: False)

    assert widget.confirm_clear_items() is False
    assert widget.export_dicts() == {"sample_a": {"alpha": 1}}
