"""Tests for QtSegmentedButton."""

from __future__ import annotations

import pytest

from qtextra.widgets.qt_button_icon import QtImagePushButton
from qtextra.widgets.qt_button_segmented import QtSegmentedButton


@pytest.fixture
def make_widget(qtbot):
    """Factory fixture for QtSegmentedButton."""

    def _widget(text: str = "Run", **kw) -> QtSegmentedButton:
        w = QtSegmentedButton(text, **kw)
        qtbot.addWidget(w)
        return w

    return _widget


class TestQtSegmentedButton:
    def test_init_default(self, make_widget):
        w = make_widget()
        assert w.text == "Run"
        assert w._actions == []
        assert w._separators == []

    def test_init_empty_text(self, make_widget):
        w = make_widget("")
        assert w.text == ""

    def test_set_text(self, make_widget):
        w = make_widget("Hello")
        w.setText("World")
        assert w.text == "World"
        assert w._main_btn.text() == "World"

    def test_add_action_returns_image_button(self, make_widget):
        w = make_widget()
        btn = w.add_action("settings", "Configure")
        assert isinstance(btn, QtImagePushButton)

    def test_add_action_appends_to_lists(self, make_widget):
        w = make_widget()
        w.add_action("settings", "Configure")
        assert len(w._actions) == 1
        assert len(w._separators) == 1

    def test_add_multiple_actions(self, make_widget):
        w = make_widget()
        w.add_action("settings", "Configure")
        w.add_action("close", "Cancel")
        assert len(w._actions) == 2
        assert len(w._separators) == 2

    def test_evt_clicked_fires_on_main_button(self, make_widget):
        w = make_widget()
        seen = []
        w.evt_clicked.connect(lambda: seen.append(1))
        w._main_btn.click()
        assert seen == [1]

    def test_evt_clicked_not_fired_by_action_button(self, make_widget):
        w = make_widget()
        seen = []
        w.evt_clicked.connect(lambda: seen.append(1))
        w.add_action("settings", "")
        w._actions[0].click()
        assert seen == []

    def test_action_single_callback_fires(self, make_widget):
        w = make_widget()
        seen = []
        w.add_action("settings", "Settings", func=lambda: seen.append("s"))
        w._actions[0].click()
        assert seen == ["s"]

    def test_action_callback_list_all_fire(self, make_widget):
        w = make_widget()
        seen = []
        w.add_action("settings", "", func=[lambda: seen.append(1), lambda: seen.append(2)])
        w._actions[0].click()
        assert seen == [1, 2]

    def test_action_no_callback_does_not_raise(self, make_widget):
        w = make_widget()
        btn = w.add_action("settings", "")
        btn.click()  # should not raise

    def test_set_enabled_false_propagates(self, make_widget):
        w = make_widget()
        w.add_action("settings", "")
        w.setEnabled(False)
        assert not w._main_btn.isEnabled()
        assert not w._actions[0].isEnabled()

    def test_set_enabled_true_restores(self, make_widget):
        w = make_widget()
        w.add_action("settings", "")
        w.setEnabled(False)
        w.setEnabled(True)
        assert w._main_btn.isEnabled()
        assert w._actions[0].isEnabled()

    def test_flat_init(self, make_widget):
        w = make_widget(flat=True)
        assert w.property("flat") == "true"

    def test_set_flat_toggle(self, make_widget):
        w = make_widget()
        w.set_flat(True)
        assert w.property("flat") == "true"
        w.set_flat(False)
        assert w.property("flat") == "false"

    def test_show_does_not_raise(self, qtbot, make_widget):
        w = make_widget("Export")
        w.add_action("save", "Save")
        w.add_action("copy", "Copy")
        w.resize(300, 40)
        w.show()
        qtbot.waitExposed(w)
