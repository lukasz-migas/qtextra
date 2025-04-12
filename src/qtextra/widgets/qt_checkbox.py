from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox


class QtTriCheckBox(QCheckBox):
    """Custom checkbox that can be in three states but only toggles true/false when user clicks."""

    def __init__(self, *args, **kwargs):
        QCheckBox.__init__(self, *args, **kwargs)
        self.clicked.connect(self.on_clicked)

    def on_clicked(self):
        """On clicked."""
        state = self.checkState()
        new_state = Qt.CheckState.Unchecked if state == Qt.CheckState.Checked else Qt.CheckState.Checked
        self.setCheckState(new_state)
