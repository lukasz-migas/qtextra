"""Tests for the search panel widget."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QPlainTextEdit

from qtextra.widgets.qt_text_search import QtSearchPanel


def test_qt_search_panel_emits_search_and_navigation(qtbot):
    widget = QtSearchPanel()
    qtbot.addWidget(widget)

    changed = []
    next_seen = []
    prev_seen = []
    widget.evt_search_changed.connect(changed.append)
    widget.evt_find_next.connect(next_seen.append)
    widget.evt_find_previous.connect(prev_seen.append)

    widget.set_search_text("alpha")
    qtbot.mouseClick(widget.next_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(widget.previous_button, Qt.MouseButton.LeftButton)

    assert changed[-1] == "alpha"
    assert next_seen == ["alpha"]
    assert prev_seen == ["alpha"]


def test_qt_search_panel_replace_and_status(qtbot):
    widget = QtSearchPanel()
    qtbot.addWidget(widget)

    replace_one = []
    replace_all = []
    widget.evt_replace_one.connect(lambda search, replace: replace_one.append((search, replace)))
    widget.evt_replace_all.connect(lambda search, replace: replace_all.append((search, replace)))

    widget.set_search_text("old")
    widget.set_replace_text("new")
    qtbot.mouseClick(widget.replace_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(widget.replace_all_button, Qt.MouseButton.LeftButton)
    widget.set_match_count(5, current=2)

    assert replace_one == [("old", "new")]
    assert replace_all == [("old", "new")]
    assert widget.match_label.text() == "2 / 5"


def test_qt_search_panel_tracks_editor_matches_and_highlights(qtbot):
    widget = QtSearchPanel()
    editor = QPlainTextEdit()
    qtbot.addWidget(widget)
    qtbot.addWidget(editor)

    editor.setPlainText("alpha beta alpha\nalpha")
    widget.set_target_editor(editor)
    widget.set_search_text("alpha")

    assert widget.match_label.text() == "1 / 3"
    assert len(editor.extraSelections()) == 3

    qtbot.mouseClick(widget.next_button, Qt.MouseButton.LeftButton)
    assert widget.match_label.text() == "2 / 3"


def test_qt_search_panel_replace_updates_editor(qtbot):
    widget = QtSearchPanel()
    editor = QPlainTextEdit()
    qtbot.addWidget(widget)
    qtbot.addWidget(editor)

    editor.setPlainText("alpha beta alpha")
    widget.set_target_editor(editor)
    widget.set_search_text("alpha")
    widget.set_replace_text("omega")

    qtbot.mouseClick(widget.replace_button, Qt.MouseButton.LeftButton)
    assert editor.toPlainText() == "omega beta alpha"
    assert widget.match_label.text() == "1 / 1"

    qtbot.mouseClick(widget.replace_all_button, Qt.MouseButton.LeftButton)
    assert editor.toPlainText() == "omega beta omega"
    assert widget.match_label.text() == "0 matches"


def test_qt_search_panel_option_toggles_emit_change(qtbot):
    widget = QtSearchPanel()
    qtbot.addWidget(widget)

    changed = []
    options_changed = []
    widget.evt_search_changed.connect(changed.append)
    widget.evt_options_changed.connect(lambda: options_changed.append(widget.search_options()))

    widget.set_search_text("needle")
    widget.case_checkbox.setChecked(True)
    widget.whole_word_checkbox.setChecked(True)
    widget.regex_checkbox.setChecked(True)

    assert options_changed[-1] == {
        "case_sensitive": True,
        "whole_word": True,
        "regex": True,
    }
    assert changed[-1] == "needle"


def test_qt_search_panel_option_toggles_refresh_editor_matches(qtbot):
    widget = QtSearchPanel()
    editor = QPlainTextEdit()
    qtbot.addWidget(widget)
    qtbot.addWidget(editor)

    editor.setPlainText("alpha alphabet alpha")
    widget.set_target_editor(editor)
    widget.set_search_text("alpha")
    assert widget.match_label.text() == "1 / 3"

    widget.whole_word_checkbox.setChecked(True)
    assert widget.match_label.text() == "1 / 2"

    widget.case_checkbox.setChecked(True)
    assert widget.match_label.text() == "1 / 2"


def test_qt_search_panel_close_and_hide_replace(qtbot):
    widget = QtSearchPanel(show_replace=False)
    qtbot.addWidget(widget)

    closed = []
    widget.evt_closed.connect(lambda: closed.append(True))
    assert widget.replace_edit.isHidden() is True

    widget.close_panel()

    assert closed == [True]
    assert widget.isHidden() is True
