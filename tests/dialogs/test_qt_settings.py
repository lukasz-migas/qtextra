"""Tests for the searchable settings dialog."""

from __future__ import annotations

import pytest

import qtextra.helpers as hp
from qtextra.dialogs.qt_settings import QtSettingsDialog


class _Dialog(QtSettingsDialog):
    def make_pages(self) -> None:
        page = self.add_page("Appearance", "mdi6.palette-outline")
        page.add_section("Theme")
        self.theme = page.add_row("Theme", hp.make_combobox(page, ["light", "dark"]))
        self.sync = page.add_row("Synchronize with local time", hp.make_checkbox(page))
        page.add_section("Text")
        self.font = page.add_row("Font size", hp.make_int_spin_box(page), tooltip="Application font size.")

        page = self.add_page("Experimental", "mdi6.flask-outline")
        self.renderer = page.add_row("Renderer", hp.make_h_layout(hp.make_checkbox(page)), keywords="opengl")


@pytest.fixture
def dialog(qtbot) -> _Dialog:
    widget = _Dialog(None, title="Settings")
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_pages_and_title(dialog: _Dialog) -> None:
    assert [page.title for page in dialog.pages] == ["Appearance", "Experimental"]
    assert dialog.current_index() == 0
    assert dialog._title.text() == "Appearance"

    dialog.set_index(1)
    assert dialog.current_index() == 1
    assert dialog._title.text() == "Experimental"


def test_search_filters_rows_sections_and_pages(dialog: _Dialog) -> None:
    dialog._search.setText("sync")
    assert not dialog.sync.isHidden()
    assert dialog.theme.isHidden()
    assert dialog.font.isHidden()
    assert dialog._list.item(1).isHidden()
    assert not dialog._list.item(0).isHidden()

    # tooltip and keywords are searchable, and the visible page follows the match
    dialog._search.setText("opengl")
    assert dialog._list.item(0).isHidden()
    assert not dialog.renderer.isHidden()
    assert dialog.current_index() == 1

    dialog._search.setText("application font")
    assert not dialog.font.isHidden()
    assert dialog.theme.isHidden()


def test_search_section_and_page_title_show_all_rows(dialog: _Dialog) -> None:
    dialog._search.setText("theme")
    assert not dialog.theme.isHidden()
    assert not dialog.sync.isHidden()
    assert dialog.font.isHidden()

    dialog._search.setText("appearance")
    assert not dialog.font.isHidden()
    assert not dialog.sync.isHidden()


def test_search_empty_state_and_clear(dialog: _Dialog) -> None:
    dialog._search.setText("does-not-exist")
    assert not dialog._empty_label.isHidden()
    assert dialog._stack.isHidden()

    dialog._search.clear()
    assert dialog._empty_label.isHidden()
    assert not dialog._stack.isHidden()
    assert all(not dialog._list.item(i).isHidden() for i in range(dialog._list.count()))
    assert not dialog.theme.isHidden()
    assert not dialog.font.isHidden()


def test_focus_search(dialog: _Dialog, qtbot) -> None:
    dialog.activateWindow()
    dialog.focus_search()
    qtbot.waitUntil(lambda: dialog._search.hasFocus(), timeout=1000)


def test_controls_share_column_width(dialog: _Dialog) -> None:
    rows = (dialog.theme, dialog.sync, dialog.font)
    for width in (900, 450):
        dialog.resize(width, 400)
        dialog.layout().activate()
        for row in rows:
            row.layout().activate()
        widths = {row.layout().itemAt(1).widget().width() for row in rows}
        assert len(widths) == 1
        assert widths.pop() <= dialog.CONTROL_WIDTH
