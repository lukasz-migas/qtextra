"""Qt dialog widgets."""
from qtpy.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt
from qtpy.QtWidgets import QDialog, QGraphicsOpacityEffect


class SubWindowBase(QDialog):
    """Sub-window mixin."""

    # Animation attributes
    FADE_IN_RATE = 220
    FADE_OUT_RATE = 120
    MAX_OPACITY = 0.9
    # Window attributes
    MIN_WIDTH = 250
    MAX_WIDTH = 350
    MIN_HEIGHT = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.SubWindow)
        self.setSizeGripEnabled(False)
        self.setModal(False)
        self.setMouseTracking(True)

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        # opacity effect
        self.opacity = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity)
        self.opacity_anim = QPropertyAnimation(self.opacity, b"opacity", self)
        # geometry effect
        self.geom_anim = QPropertyAnimation(self, b"geometry", self)

    def move_to(self, location):
        """Move to location."""
        if location == "top_right":
            self.move_to_top_right()
        elif location == "top_left":
            self.move_to_top_left()
        elif location == "bottom_right":
            self.move_to_bottom_right()
        elif location == "bottom_left":
            self.move_to_bottom_left()

    def move_to_top_right(self, offset=(-10, 10)):
        """Position widget at the top right edge of the parent."""
        if not self.parent():
            return
        psz = self.parent().size()
        sz = psz - QSize(self.size().width(), psz.height()) + QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))

    def move_to_bottom_right(self, offset=(8, 8)):
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - self.size() - QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))

    def move_to_top_left(self, offset=(8, 8)):
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        self.move(QPoint(*offset))

    def move_to_bottom_left(self, offset=(8, 8)):
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - self.size()
        self.move(QPoint(offset[0], sz.height() - offset[1]))

    def slide_in(self):
        """Run animation that fades in the dialog with a slight slide up."""
        geom = self.geometry()
        self.geom_anim.setDuration(self.FADE_IN_RATE)
        self.geom_anim.setStartValue(geom.translated(0, -20))
        self.geom_anim.setEndValue(geom)
        self.geom_anim.setEasingCurve(QEasingCurve.OutQuad)
        # fade in
        self.opacity_anim.setDuration(self.FADE_IN_RATE)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(self.MAX_OPACITY)
        self.geom_anim.start()
        self.opacity_anim.start()

    def fade_in(self):
        """Run animation that fades in the dialog."""
        self.opacity_anim.setDuration(self.FADE_IN_RATE)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(self.MAX_OPACITY)
        self.opacity_anim.start()

    def fade_out(self):
        """Run animation that fades out the dialog."""
        self.opacity_anim.setDuration(self.FADE_OUT_RATE)
        self.opacity_anim.setStartValue(self.MAX_OPACITY)
        self.opacity_anim.setEndValue(0)
        self.opacity_anim.start()

    def close(self):
        """Fade out then close."""
        try:
            super().close()
        except (RuntimeError, TypeError):
            pass
