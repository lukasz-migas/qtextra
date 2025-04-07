"""Splash screen."""

from koyo.typing import PathLike
from qtpy.QtCore import Qt, Slot  # type: ignore[attr-defined]
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QSplashScreen

import qtextra.helpers as hp


class QtSplashScreen(QSplashScreen):
    """Splash screen."""

    TITLE = "qtextra"

    def __init__(self, path: PathLike, width: int = 360):
        from qtextra.config import EVENTS
        from qtextra.event_loop import get_app

        get_app()
        pm = QPixmap(path).scaled(
            width, width, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        super().__init__(pm)
        self.show()
        hp.set_font(self, font_size=16)
        self.showMessage(f"Loading {self.TITLE}...", alignment=Qt.AlignmentFlag.AlignLeft, color=Qt.GlobalColor.black)

        EVENTS.evt_splash_msg.connect(self.on_message)
        EVENTS.evt_splash_close.connect(self.close)

    @Slot(str)  # type: ignore[misc]
    def on_message(self, msg: str):
        """Show message."""
        self.showMessage(msg, alignment=Qt.AlignmentFlag.AlignLeft, color=Qt.GlobalColor.white)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.assets import ICONS
    from qtextra.utils.dev import qapplication

    app = qapplication()

    random_icon = next(iter(ICONS.values()))

    wdg = QtSplashScreen(random_icon)
    wdg.show()
    wdg.raise_()
    hp.call_later(wdg, wdg.close, delay=2000)
    sys.exit(app.exec_())
