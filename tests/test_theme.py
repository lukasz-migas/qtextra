"""Test theme."""

import json

import pytest

from qtextra.config.theme import DARK_THEME, LIGHT_THEME, THEMES, Theme, Themes


def test_themes(qtbot):
    assert THEMES, "THemes should initialized"
    assert len(THEMES.themes) >= 2, "Expected at least two themes"
    assert "dark" in THEMES.themes, "Expected theme dark"
    assert "light" in THEMES.themes, "Expected theme light"

    theme = THEMES["dark"]

    # check font size handling
    assert theme.font_size.endswith("pt")
    theme.font_size = 14
    assert theme.font_size == "14pt"

    THEMES.theme = "dark"
    theme = THEMES.active
    assert theme.name == "dark"
    assert THEMES.is_dark, "Expect dark theme."

    THEMES.theme = "light"
    theme = THEMES.active
    assert theme.name == "light"
    assert not THEMES.is_dark, "Expected light theme."
    theme.font_size = 10
    assert THEMES.get_font_size() == 10
    theme.success = "#FF00FF"
    assert THEMES.get_hex_color("success") == "#ff00ff"
    assert THEMES.get_rgb_color("success") == "rgb(255, 0, 255)"

    qss = THEMES.get_theme_stylesheet()
    assert isinstance(qss, str), "QSS should be a string"

    with qtbot.waitSignals([THEMES.evt_theme_icon_changed], timeout=500):
        theme.icon = "#00ff00"
    with qtbot.waitSignals([THEMES.evt_theme_changed], timeout=500):
        theme.font_size = 16


def test_get_theme_as_dict_returns_serialized_colors():
    themes = Themes()

    theme = themes.get_theme("dark", as_dict=True)

    assert isinstance(theme["success"], str)
    assert theme["success"] == "#1ed760"
    assert isinstance(theme["info"], str)


def test_loading_legacy_theme_config_without_info_keeps_default(tmp_path):
    themes = Themes()
    legacy_dark = dict(DARK_THEME)
    legacy_dark.pop("info")

    config_path = tmp_path / "themes-config.json"
    config_path.write_text(
        json.dumps(
            {
                "settings": {"theme": "dark", "sync_with_time": False},
                "themes": {"dark": legacy_dark},
            }
        )
    )

    themes.load_config(config_path)

    assert themes["dark"].info.as_hex() == Theme(**DARK_THEME).info.as_hex()


def test_added_theme_emits_theme_changed(qtbot):
    themes = Themes()
    custom_theme = Theme(**{**LIGHT_THEME, "name": "custom"})
    themes.add_theme("custom", custom_theme)

    with qtbot.waitSignal(themes.evt_theme_changed, timeout=500):
        custom_theme.font_size = 16


def test_added_theme_emits_theme_added(qtbot):
    themes = Themes()

    with qtbot.waitSignal(themes.evt_theme_added, timeout=500):
        themes.add_theme("custom", Theme(**{**LIGHT_THEME, "name": "custom"}))


def test_loading_multiple_new_themes_binds_icon_updates_to_correct_theme(monkeypatch):
    themes = Themes()
    recorded = []
    monkeypatch.setattr(themes, "register_themes", lambda names=None: recorded.extend(names or []))

    themes._set_config_parameters(
        {
            "themes": {
                "custom_a": {**LIGHT_THEME, "name": "custom_a"},
                "custom_b": {**DARK_THEME, "name": "custom_b"},
            }
        }
    )

    themes["custom_a"].icon = "#123456"
    themes["custom_b"].icon = "#654321"

    assert recorded == ["custom_a", "custom_b"]


def test_setting_unknown_theme_raises_value_error():
    themes = Themes()

    with pytest.raises(ValueError, match="Unrecognized theme"):
        themes.theme = "missing-theme"
