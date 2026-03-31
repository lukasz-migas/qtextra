"""DialogThemeEditor example."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_theme_editor import DialogThemeEditor
from qtextra.dialogs.qt_theme_sample import QtSampleWidget

app = QApplication([])

preview_target = QtSampleWidget()
preview_target.setWindowTitle("Theme target")
preview_target.resize(900, 700)
THEMES.apply(preview_target)
preview_target.show()

editor = DialogThemeEditor(None, dlg=preview_target)
editor.resize(300, 700)
THEMES.apply(editor)
editor.show_right_of_widget(preview_target)

app.exec_()
