"""Tests for compact attribute tag widgets."""

from __future__ import annotations

import pytest
from qtpy.QtCore import QPoint, Qt

from qtextra.widgets.qt_button_attribute import QtAttributeTagManager
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayoutWidget


def test_attribute_manager_add_update_and_export(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)

    changed = []
    added = []
    updated = []
    manager.evt_items_changed.connect(changed.append)
    manager.evt_item_added.connect(lambda key, value: added.append((key, value)))
    manager.evt_item_updated.connect(lambda old, new, value: updated.append((old, new, value)))

    assert manager.add_item("name", "alpha") is True
    assert manager.add_item("count", 3) is True
    assert manager.add_item("ratio", 1.5) is True
    assert manager.add_item("missing", None) is True
    assert manager.add_item("COUNT", 4) is True

    assert manager.export_dict() == {
        "name": "alpha",
        "COUNT": 4,
        "ratio": 1.5,
        "missing": None,
    }
    assert added[-1] == ("missing", None)
    assert updated[-1] == ("count", "COUNT", 4)
    assert changed[-1] == manager.export_dict()
    assert manager.get_value("count") == 4
    assert manager.has_item("MISSING") is True


def test_attribute_manager_set_items_preserves_order_and_clear(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)
    manager.set_items({"first": 1, "second": 2, "third": 3})

    changed = []
    manager.evt_items_changed.connect(changed.append)

    assert list(manager.items()) == ["first", "second", "third"]
    assert manager.remove_item("SECOND") is True
    assert manager.items() == {"first": 1, "third": 3}

    manager.clear_items()
    assert manager.items() == {}
    assert changed[-1] == {}


def test_attribute_manager_rejects_invalid_programmatic_values(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)

    assert manager.add_item("", 1) is False
    with pytest.raises(TypeError):
        manager.add_item("bad", [])


def test_attribute_tag_text_and_delete_action(qtbot):
    manager = QtAttributeTagManager(tag_maximum_width=120)
    qtbot.addWidget(manager)
    manager.set_items({"a_long_attribute_name": "a_long_attribute_value", "missing": None})

    long_tag = manager.widgets["a_long_attribute_name"]
    assert long_tag.text == "a_long_attribute_name: a_long_attribute_value"
    assert long_tag.toolTip() == long_tag.text
    assert long_tag.maximumWidth() == 120
    assert manager.widgets["missing"].text == "missing: None"

    long_tag.delete_button.click()
    assert manager.items() == {"missing": None}


def test_attribute_popup_adds_typed_values(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)
    manager.show()

    manager.add_button.click()
    popup = manager._popup
    assert popup.isVisible()

    popup.key_edit.setText("count")
    popup.type_combo.setCurrentText("int")
    popup.value_edit.setText("10")
    qtbot.keyClick(popup.value_edit, Qt.Key.Key_Return)

    assert manager.items() == {"count": 10}
    assert popup.isVisible() is False

    manager.add_button.click()
    popup.key_edit.setText("empty")
    popup.type_combo.setCurrentText("None")
    assert popup.value_edit.isEnabled() is False
    popup.save_button.click()
    assert manager.items() == {"count": 10, "empty": None}


def test_attribute_popup_edits_and_renames_in_place(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)
    manager.set_items({"first": 1, "second": 2, "third": 3})
    manager.show()

    assert manager.edit_item("second") is True
    popup = manager._popup
    assert popup.key_edit.text() == "second"
    assert popup.value_edit.text() == "2"
    assert popup.type_combo.currentText() == "int"

    popup.key_edit.setText("renamed")
    popup.type_combo.setCurrentText("float")
    popup.value_edit.setText("2.5")
    popup.save_button.click()

    assert manager.items() == {"first": 1, "renamed": 2.5, "third": 3}
    assert manager.widgets["renamed"].text == "renamed: 2.5"


def test_attribute_popup_rejects_duplicates_and_invalid_input(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)
    manager.set_items({"alpha": 1, "beta": 2})
    manager.show()

    manager.edit_item("beta")
    popup = manager._popup
    popup.key_edit.setText("ALPHA")
    popup.save_button.click()
    assert popup.isVisible()
    assert "already exists" in popup.error_label.text()
    assert popup.key_edit.property("invalid") is True
    assert manager.items() == {"alpha": 1, "beta": 2}

    popup.key_edit.clear()
    popup.save_button.click()
    assert popup.error_label.text() == "Key cannot be empty."

    popup.key_edit.setText("beta")
    popup.type_combo.setCurrentText("float")
    popup.value_edit.setText("")
    popup.save_button.click()
    assert popup.error_label.text() == "Float value cannot be empty."
    assert popup.value_edit.property("invalid") is True
    assert popup.key_edit.property("invalid") is False
    assert manager.items() == {"alpha": 1, "beta": 2}


def test_attribute_popup_escape_cancels_changes(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)
    manager.set_items({"alpha": 1})
    manager.show()

    manager.edit_item("alpha")
    popup = manager._popup
    popup.key_edit.setText("changed")
    popup.value_edit.setText("99")
    qtbot.keyClick(popup.key_edit, Qt.Key.Key_Escape)
    qtbot.waitUntil(lambda: not popup.isVisible())

    assert manager.items() == {"alpha": 1}


def test_attribute_pill_click_opens_editor(qtbot):
    manager = QtAttributeTagManager()
    qtbot.addWidget(manager)
    manager.set_items({"alpha": "one"})
    manager.show()

    tag = manager.widgets["alpha"]
    qtbot.mouseClick(tag, Qt.MouseButton.LeftButton, pos=QPoint(4, tag.height() // 2))

    assert manager._popup.isVisible()
    assert manager._popup.key_edit.text() == "alpha"


def test_attribute_manager_layout_modes_keep_add_button_separate(qtbot):
    flow_manager = QtAttributeTagManager(flow=True)
    scroll_manager = QtAttributeTagManager(flow=False)
    qtbot.addWidget(flow_manager)
    qtbot.addWidget(scroll_manager)

    flow_manager.add_items({"one": 1, "two": 2})
    scroll_manager.add_items({"one": 1, "two": 2})

    assert not isinstance(flow_manager._tag_layout, QtScrollableHLayoutWidget)
    assert isinstance(scroll_manager._tag_layout, QtScrollableHLayoutWidget)
    assert flow_manager.layout().indexOf(flow_manager.add_button) >= 0
    assert scroll_manager.layout().indexOf(scroll_manager.add_button) >= 0
    assert len(scroll_manager.widgets) == 2
    assert scroll_manager._tag_layout._main_layout.indexOf(scroll_manager.add_button) == -1

    scroll_manager.resize(240, 60)
    scroll_manager.show()
    assert scroll_manager.add_button.geometry().right() <= scroll_manager.contentsRect().right()


def test_attribute_manager_case_sensitive_keys(qtbot):
    manager = QtAttributeTagManager(case_sensitive=True)
    qtbot.addWidget(manager)

    assert manager.add_item("Alpha", 1) is True
    assert manager.add_item("alpha", 2) is True
    assert manager.items() == {"Alpha": 1, "alpha": 2}
