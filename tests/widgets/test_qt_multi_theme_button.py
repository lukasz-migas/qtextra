from __future__ import annotations

import pytest

from qtextra.config import THEMES
from qtextra.widgets.qt_button_icon import QtMultiThemeButton


@pytest.fixture
def restore_global_theme():
    previous_theme = THEMES.theme
    try:
        yield
    finally:
        THEMES.theme = previous_theme


def test_qt_multi_theme_button_lists_all_available_themes(qtbot, restore_global_theme):
    widget = QtMultiThemeButton()
    qtbot.addWidget(widget)

    state_to_option = widget.get_state_to_option()
    state_to_icon = widget.get_state_to_icon()

    assert set(state_to_option) == set(THEMES.available_themes())
    assert set(state_to_icon) == set(THEMES.available_themes())
    assert state_to_option["shades_of_purple"] == "Shades Of Purple"
    assert state_to_option["synthwave_84"] == "Synthwave 84"
    assert state_to_icon["light"] == "light_theme"
    assert state_to_icon["monokai"] == "dark_theme"


def test_qt_multi_theme_button_auto_connect_updates_global_theme(qtbot, restore_global_theme):
    THEMES.theme = "light"

    widget = QtMultiThemeButton(auto_connect=True)
    qtbot.addWidget(widget)

    widget.set_state("dracula")

    assert THEMES.theme == "dracula"
    assert widget.state == "dracula"


def test_qt_multi_theme_button_tracks_external_theme_changes(qtbot, restore_global_theme):
    THEMES.theme = "light"

    widget = QtMultiThemeButton()
    qtbot.addWidget(widget)

    THEMES.theme = "monokai"

    assert widget.state == "monokai"
