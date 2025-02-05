"""Modified SystemTrayIcon."""

# Third-party imports
from qtpy.QtWidgets import QSystemTrayIcon


class QtSystemTrayIcon(QSystemTrayIcon):
    """Modified SystemTrayIcon."""

    is_destroyed = False

    def __init__(self, parent):
        super().__init__(parent)

    def deleteLater(self):
        """Override deleteLater method to set the state of the object."""
        self.is_destroyed = True
        super(QSystemTrayIcon, self).deleteLater()
