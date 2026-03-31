# `DialogThemeEditor`

`DialogThemeEditor` provides a live editor for `qtextra` themes. It can:

- switch between registered themes
- duplicate the current theme into a new editable theme
- edit all built-in theme colors
- update theme type, console syntax style, and font sizes
- restore the bundled `dark` and `light` defaults
- save the current theme configuration through `THEMES.save_config()`

## Basic Usage

```python
from qtpy.QtWidgets import QApplication, QWidget

from qtextra.config import THEMES
from qtextra.dialogs.qt_theme_editor import DialogThemeEditor

app = QApplication([])

preview_target = QWidget()
preview_target.resize(900, 700)
THEMES.apply(preview_target)
preview_target.show()

editor = DialogThemeEditor(None, dlg=preview_target)
editor.show()

app.exec_()
```

If `dlg` is omitted, the editor opens its built-in preview dialog using the
sample widget from [`qt_theme_sample.py`](../../src/qtextra/dialogs/qt_theme_sample.py).

## Notes

- Color fields use the library's `QtColorSwatch` widget.
- Font sizes are stored in the theme config as point sizes.
- Console syntax styling is backed by available Pygments styles.
- New themes are registered with the theme manager so theme-aware widgets can
  discover them immediately.

Runnable example: [`examples/dialog_theme_editor.py`](../../examples/dialog_theme_editor.py)
