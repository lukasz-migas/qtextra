from __future__ import annotations

from qtpy.QtWidgets import QComboBox, QSpinBox, QWidget

from qtextra.config.theme import DARK_THEME, Themes
from qtextra.dialogs import qt_theme_editor as editor_mod
from qtextra.widgets.qt_button_color import QtColorSwatch


def _make_dialog(qtbot, monkeypatch):
    themes = Themes()
    monkeypatch.setattr(editor_mod, "THEMES", themes)
    monkeypatch.setattr(themes, "register_themes", lambda names=None: None)
    preview_target = QWidget()
    qtbot.addWidget(preview_target)
    dialog = editor_mod.DialogThemeEditor(None, dlg=preview_target)
    qtbot.addWidget(dialog)
    return dialog, themes, preview_target


def test_theme_editor_builds_full_editor_surface(qtbot, monkeypatch):
    dialog, themes, _ = _make_dialog(qtbot, monkeypatch)

    assert dialog.theme.currentText() == themes.theme
    assert dialog.theme_name_value.text() == themes.theme
    assert isinstance(dialog.widgets["type"], QComboBox)
    assert isinstance(dialog.widgets["syntax_style"], QComboBox)
    assert isinstance(dialog.widgets["font_size"], QSpinBox)
    assert dialog.widgets["font_size"].suffix().strip() == "pt"
    assert isinstance(dialog.widgets["header_size"], QSpinBox)

    for key in editor_mod.COLOR_KEYS:
        assert isinstance(dialog.widgets[key], QtColorSwatch)


def test_theme_editor_updates_theme_values_live(qtbot, monkeypatch):
    dialog, themes, preview_target = _make_dialog(qtbot, monkeypatch)
    seen_stylesheets = []

    def _record_stylesheet(widget, theme_name=None):
        seen_stylesheets.append((widget, theme_name))

    monkeypatch.setattr(themes, "set_theme_stylesheet", _record_stylesheet)

    dialog.widgets["font_size"].setValue(17)
    assert themes["light"].font_size == "17pt"

    dialog.widgets["syntax_style"].setCurrentText("monokai")
    assert themes["light"].syntax_style == "monokai"

    dialog.widgets["type"].setCurrentText("dark")
    assert themes["light"].type == "dark"

    dialog.widgets["success"].set_color("#112233")
    assert themes.get_hex_color("success") == "#112233"

    assert seen_stylesheets
    assert all(widget is preview_target for widget, _ in seen_stylesheets)
    assert all(theme_name == "light" for _, theme_name in seen_stylesheets)


def test_theme_editor_can_add_new_theme(qtbot, monkeypatch):
    dialog, themes, _ = _make_dialog(qtbot, monkeypatch)
    monkeypatch.setattr(editor_mod.hp, "get_text", lambda *args, **kwargs: "custom ocean")

    with qtbot.waitSignal(themes.evt_theme_added, timeout=500):
        dialog.on_add_new_theme()

    assert "custom ocean" in themes.themes
    assert themes["custom ocean"].font_size == themes["light"].font_size
    assert dialog.theme.currentText() == "custom ocean"
    assert themes.theme == "custom ocean"
    assert dialog.theme_name_value.text() == "custom ocean"


def test_theme_editor_restores_builtin_theme_defaults(qtbot, monkeypatch):
    dialog, themes, _ = _make_dialog(qtbot, monkeypatch)

    dialog.theme.setCurrentText("dark")
    themes["dark"].font_size = "22pt"
    themes["dark"].success = "#0c1824"

    dialog.on_restore_theme()

    assert themes["dark"].font_size == DARK_THEME["font_size"]
    assert themes["dark"].success.as_hex() == "#1ed760"


def test_theme_editor_restores_all_builtin_defaults(qtbot, monkeypatch):
    dialog, themes, _ = _make_dialog(qtbot, monkeypatch)

    themes["dark"].font_size = "22pt"
    themes["light"].font_size = "21pt"
    themes["dark"].success = "#0c1824"
    themes["light"].info = "#102030"

    dialog.on_restore_all_defaults()

    assert themes["dark"].font_size == DARK_THEME["font_size"]
    assert themes["light"].font_size == editor_mod.LIGHT_THEME["font_size"]
    assert themes["dark"].success.as_hex() == "#1ed760"
    assert themes["light"].info.as_hex() == "#007acc"
