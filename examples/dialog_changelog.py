"""QtPopout example."""

from koyo.release import format_version, get_latest_git
from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_changelog import ChangelogDialog

app = QApplication([])
data = get_latest_git(user="pyapp-kit", package="superqt")
text = format_version(data)
widget = ChangelogDialog(None, text)
THEMES.apply(widget)
widget.exec_()
