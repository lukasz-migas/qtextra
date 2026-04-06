"""QtPopout example."""

from koyo.release import format_version, get_latest_git
from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_changelog import QtChangelogDialog

app = QApplication([])
data = get_latest_git(user="lukasz-migas", package="qtextra")
text = format_version(data)
widget = QtChangelogDialog(None, text)
THEMES.apply(widget)
widget.exec_()
