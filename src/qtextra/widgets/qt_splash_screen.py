"""Splash screen."""
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QSplashScreen

import qtextra.helpers as hp


class QtSplashScreen(QSplashScreen):
    """Splash screen."""

    TITLE = "qtextra"

    def __init__(self, width: int = 360):
        from ionglow.app.event_loop import ICON_PATH, get_app

        from qtextra.config import EVENTS

        get_app()
        pm = QPixmap(ICON_PATH).scaled(width, width, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        super().__init__(pm)
        self.show()
        hp.set_font(self, font_size=16)
        self.showMessage(f"Loading {self.TITLE}...", alignment=Qt.AlignmentFlag.AlignLeft, color=Qt.black)

        EVENTS.evt_splash_msg.connect(self.on_message)
        EVENTS.evt_splash_close.connect(self.close)

    @Slot(str)
    def on_message(self, msg: str):
        """Show message."""
        self.showMessage(msg, alignment=Qt.AlignmentFlag.AlignLeft, color=Qt.white)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)

    _ = QtSplashScreen()
    sys.exit(app.exec_())
