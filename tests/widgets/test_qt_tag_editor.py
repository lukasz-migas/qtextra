"""Tests for the tag editor widget."""

from __future__ import annotations

from qtpy.QtCore import Qt

from qtextra.widgets.qt_tag_editor import QtTagEditor


def test_qt_tag_editor_add_and_deduplicate(qtbot):
    widget = QtTagEditor()
    qtbot.addWidget(widget)

    added = []
    changed = []
    widget.evt_tag_added.connect(added.append)
    widget.evt_tags_changed.connect(changed.append)

    assert widget.add_tag("Alpha") is True
    assert widget.add_tag("alpha") is False
    assert widget.tags() == ["Alpha"]
    assert added == ["Alpha"]
    assert changed[-1] == ["Alpha"]


def test_qt_tag_editor_adds_tokens_from_text_input(qtbot):
    widget = QtTagEditor()
    qtbot.addWidget(widget)

    widget.text_edit.setText("one, two;three")

    assert widget.tags() == ["one", "two", "three"]
    assert widget.text_edit.text() == ""


def test_qt_tag_editor_return_adds_current_text(qtbot):
    widget = QtTagEditor()
    qtbot.addWidget(widget)

    widget.text_edit.setText("release")
    qtbot.keyClick(widget.text_edit, Qt.Key.Key_Return)

    assert widget.tags() == ["release"]


def test_qt_tag_editor_remove_and_replace_tags(qtbot):
    widget = QtTagEditor()
    qtbot.addWidget(widget)
    widget.set_tags(["alpha", "beta", "gamma"])

    removed = []
    widget.evt_tag_removed.connect(removed.append)

    assert widget.remove_tag("beta") is True
    assert widget.tags() == ["alpha", "gamma"]
    assert removed == ["beta"]

    widget.set_tags(["one", "one", "", "two"])
    assert widget.tags() == ["one", "two"]


def test_qt_tag_editor_scroll_mode_preserves_order(qtbot):
    widget = QtTagEditor(flow=False)
    qtbot.addWidget(widget)
    widget.add_tags(["first", "second", "third"])

    assert widget.tags() == ["first", "second", "third"]
    assert widget.has_tag("second") is True
