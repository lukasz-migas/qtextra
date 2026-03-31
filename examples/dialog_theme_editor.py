"""DialogThemeEditor example."""

from qtpy.QtWidgets import QApplication, QWidget

from qtextra.config import THEMES
from qtextra.dialogs.qt_theme_editor import DialogThemeEditor

app = QApplication([])

preview_target = QWidget()
preview_target.setWindowTitle("Theme target")
preview_target.resize(900, 700)
THEMES.apply(preview_target)
preview_target.show()

editor = DialogThemeEditor(None, dlg=preview_target)
editor.show()

app.exec_()
