# `DialogThemeEditor`

`DialogThemeEditor` provides a live editor for `qtextra` themes. It can:

- switch between registered themes
- duplicate the current theme into a new editable theme
- edit all built-in theme colors
- update theme type, console syntax style, and font sizes
- restore the bundled `dark` and `light` defaults
- save the current theme configuration through `THEMES.save_config()`

## Basic Usage

{{ show_example('dialog_theme_editor.py', 760) }}

Source: [`examples/dialog_theme_editor.py`](../../examples/dialog_theme_editor.py)

{{ include_example('dialog_theme_editor.py') }}

If `dlg` is omitted, the editor opens its built-in preview dialog using the
sample widget from [`qt_theme_sample.py`](../../src/qtextra/dialogs/qt_theme_sample.py).

## Notes

- Color fields use the library's `QtColorSwatch` widget.
- Font sizes are stored in the theme config as point sizes.
- Console syntax styling is backed by available Pygments styles.
- New themes are registered with the theme manager so theme-aware widgets can
  discover them immediately.
