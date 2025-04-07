"""Test theme."""

from qtextra.config.theme import THEMES


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
