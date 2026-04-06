"""Dialog to edit theme."""

from __future__ import annotations

from functools import partial

import numpy as np
from loguru import logger
from pydantic_extra_types.color import Color
from pygments.styles import STYLE_MAP
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.config.theme import Theme, get_builtin_theme_data
from qtextra.widgets.qt_button_color import QtColorSwatch
from qtextra.widgets.qt_dialog import QtDialog

COLOR_KEYS = (
    "background",
    "foreground",
    "primary",
    "secondary",
    "highlight",
    "text",
    "icon",
    "warning",
    "error",
    "success",
    "info",
    "progress",
    "current",
    "console",
    "canvas",
    "standout",
)
SIZE_KEYS = ("font_size", "header_size")
GENERAL_KEYS = ("type", "syntax_style")
THEME_TYPE_OPTIONS = ("dark", "light")
STYLE_OPTIONS = tuple(sorted(STYLE_MAP))


def _field_label(key: str) -> str:
    """Format a field name for display."""
    return key.replace("_", " ").title()


def _font_size_value(value: str | int) -> int:
    """Normalize a theme size to a spin-box value."""
    if isinstance(value, int):
        return value
    return int(str(value).replace("px", "").replace("pt", ""))


class QtThemeEditorDialog(QtDialog):
    """Theme editor."""

    def __init__(self, parent, dlg: QWidget | None = None):
        self.dlg = dlg
        self.widgets: dict[str, QWidget] = {}
        super().__init__(parent, title="Theme Editor")
        if self.dlg is None:
            self.on_preview()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make panel."""
        theme_label = hp.make_label(self, "Theme")
        self.theme = hp.make_combobox(self, THEMES.available_themes(), value=THEMES.theme)
        self.theme.currentTextChanged.connect(self.on_set_theme)

        self.new_theme_btn = hp.make_qta_btn(self, "add")
        self.new_theme_btn.setToolTip("Duplicate the current theme")
        self.new_theme_btn.clicked.connect(self.on_add_new_theme)

        self.restore_btn = hp.make_btn(self, "Restore Theme Defaults")
        self.restore_btn.clicked.connect(self.on_restore_theme)
        self.restore_all_btn = hp.make_btn(self, "Restore Built-in Defaults")
        self.restore_all_btn.clicked.connect(self.on_restore_all_defaults)

        self.theme_name_value = hp.make_label(self, "")

        self.general_form = hp.make_form_layout(spacing=4)
        self.sizes_form = hp.make_form_layout(spacing=4)
        self.colors_form = hp.make_form_layout(spacing=4)
        self._populate_theme_form()

        general_box = hp.make_group_box(self, "Theme Settings")
        general_box.setLayout(
            hp.make_v_layout(
                hp.make_form_layout(
                    (hp.make_label(self, "Theme Name"), self.theme_name_value),
                    spacing=4,
                ),
                self.general_form,
                self.sizes_form,
                spacing=8,
            )
        )

        colors_box = hp.make_group_box(self, "Theme Colors")
        colors_box.setLayout(hp.make_v_layout(self.colors_form))

        scroll_inner, scroll = hp.make_scroll_area(self, horizontal=Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_inner.setLayout(hp.make_v_layout(general_box, colors_box, spacing=12))

        save_btn = hp.make_btn(self, "Save themes")
        save_btn.clicked.connect(self.on_save_theme)

        vertical_layout = hp.make_v_layout(
            hp.make_h_layout(theme_label, self.theme, self.new_theme_btn, stretch_id=1),
            scroll,
            hp.make_h_layout(self.restore_btn, self.restore_all_btn, save_btn, stretch_before=True),
            spacing=10,
        )
        self.on_set_theme()
        return vertical_layout

    def _populate_theme_form(self) -> None:
        """Create controls for all editable theme fields."""
        for key in GENERAL_KEYS + SIZE_KEYS + COLOR_KEYS:
            label = hp.make_label(self, _field_label(key))
            widget = self._make_editor_widget(key)
            self.widgets[key] = widget
            if key in GENERAL_KEYS:
                self.general_form.addRow(label, widget)
            elif key in SIZE_KEYS:
                self.sizes_form.addRow(label, widget)
            else:
                self.colors_form.addRow(label, widget)

    def _make_editor_widget(self, key: str) -> QWidget:
        """Create an editor widget for a theme field."""
        if key == "type":
            return hp.make_combobox(
                self,
                THEME_TYPE_OPTIONS,
                value=THEMES.active.type,
                func=partial(self.on_text_change, key),
            )
        if key == "syntax_style":
            combo = hp.make_combobox(self, STYLE_OPTIONS, value=THEMES.active.syntax_style)
            combo.currentTextChanged.connect(partial(self.on_text_change, key))
            return combo
        if key in SIZE_KEYS:
            value = _font_size_value(getattr(THEMES.active, key))
            spin = hp.make_int_spin_box(
                self,
                minimum=6,
                maximum=48,
                step_size=1,
                value=value,
                suffix=" pt",
                keyboard_tracking=False,
            )
            spin.valueChanged.connect(partial(self.on_fontsize_change, key))
            return spin
        if key in COLOR_KEYS:
            color = getattr(THEMES.active, key)
            swatch = hp.make_swatch(
                self,
                color.as_hex(),
                value=color.as_hex(),
                tooltip=f"Change {_field_label(key).lower()}",
            )
            swatch.evt_color_changed.connect(partial(self.on_color_change, key))
            swatch.setMinimumHeight(28)
            return swatch
        raise KeyError(f"Unsupported theme field: {key}")

    @staticmethod
    def on_save_theme() -> None:
        """Save theme."""
        THEMES.save_config()

    def on_restore_theme(self) -> None:
        """Restore original theme."""
        theme_name = self.theme.currentText()
        if theme_name not in {"dark", "light"}:
            return

        theme_data = get_builtin_theme_data(theme_name)
        restored_theme = Theme(**theme_data)
        for key, value in restored_theme:
            setattr(THEMES.themes[theme_name], key, value)
        self.on_set_theme(theme_name)
        logger.debug(f"Restored defaults for '{theme_name}'")

    def on_restore_all_defaults(self) -> None:
        """Restore built-in defaults for all bundled themes."""
        for theme_name in ("dark", "light"):
            theme_data = get_builtin_theme_data(theme_name)
            restored_theme = Theme(**theme_data)
            for key, value in restored_theme:
                setattr(THEMES.themes[theme_name], key, value)
        self.on_set_theme(self.theme.currentText())
        logger.debug("Restored built-in theme defaults")

    def _set_widget_value(self, key: str, value: str | Color) -> None:
        """Synchronize the UI control for a field."""
        widget = self.widgets[key]
        with hp.qt_signals_blocked(widget):
            if isinstance(widget, QComboBox):
                widget.setCurrentText(str(value))
            elif isinstance(widget, QtColorSwatch):
                widget.set_color(value.as_hex(), force=True)
            else:
                widget.setValue(_font_size_value(value))

    def on_set_theme(self, theme_name: str | None = None) -> None:
        """Update theme."""
        theme_name = theme_name or self.theme.currentText()
        hp.disable_widgets(self.restore_btn, disabled=theme_name not in {"dark", "light"})

        theme_data = THEMES[theme_name]
        self.theme_name_value.setText(theme_data.name)
        for key, value in theme_data:
            if key in self.widgets:
                self._set_widget_value(key, value)

        THEMES.theme = theme_name
        if self.dlg is not None:
            THEMES.set_theme_stylesheet(self.dlg, theme_name)
        logger.debug(f"Set theme '{theme_name}'")

    def on_add_new_theme(self) -> None:
        """Add new theme."""
        new_theme = hp.get_text(self, "New theme name", "New theme name", f"{THEMES.theme} - copy")
        if new_theme is None:
            return

        new_theme = new_theme.strip()
        if not new_theme or new_theme in THEMES.themes:
            return

        theme_data = THEMES.get_theme().to_dict()
        theme_data["name"] = new_theme
        THEMES.add_theme(new_theme, theme_data, register=True)
        self.theme.insertItem(0, new_theme)
        self.theme.setCurrentText(new_theme)
        logger.debug(f"Added new theme '{new_theme}'")

    def _update_live_theme(self, key: str, value: str | np.ndarray) -> None:
        """Update the active theme and refresh the preview."""
        theme = self.theme.currentText()
        setattr(THEMES.themes[theme], key, value)
        if self.dlg is not None:
            THEMES.set_theme_stylesheet(self.dlg, theme)

    def on_text_change(self, key: str, value: str) -> None:
        """Update text fields in the current theme."""
        self._update_live_theme(key, value)

    def on_color_change(self, key: str, new_color: np.ndarray) -> None:
        """Update color in dictionary."""
        self._update_live_theme(key, new_color[0:3] * 255)

    def on_fontsize_change(self, key: str, value: int) -> None:
        """Update font size in dictionary."""
        self._update_live_theme(key, f"{value}pt")

    def on_preview(self) -> None:
        """Preview theme."""
        if self.dlg is None:
            self.dlg = PreviewDialog(self)
            THEMES.set_theme_stylesheet(self.dlg)
            self.dlg.show()


class PreviewDialog(QtDialog):
    """Preview dialog."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)

    def closeEvent(self, event) -> None:
        """Close window."""
        event.ignore()

    def make_panel(self) -> QLayout:
        """Make panel."""
        from qtpy.QtWidgets import QHBoxLayout

        from qtextra.dialogs.qt_theme_sample import QtSampleWidget

        main_layout = QHBoxLayout()
        main_layout.addWidget(QtSampleWidget(), stretch=True)
        return main_layout


# For backwards compatibility
DialogThemeEditor = QtThemeEditorDialog


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    _ = qapplication()  # analysis:ignore
    dlg = DialogThemeEditor(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
