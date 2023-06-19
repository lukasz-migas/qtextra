from qtpy.QtWidgets import QLabel


class QImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.pixmap_width: int = 1
        self.pixmap_height: int = 1

    def setPixmap(self, pm) -> None:
        self.pixmap_width = pm.width()
        self.pixmap_height = pm.height()
        self.update_margins()
        super().setPixmap(pm)

    def resizeEvent(self, a0) -> None:
        self.update_margins()
        super().resizeEvent(a0)

    def update_margins(self):
        if self.pixmap() is None:
            return
        pixmapWidth = self.pixmap().width()
        pixmap_height = self.pixmap().height()
        if pixmapWidth <= 0 or pixmap_height <= 0:
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        if w * pixmap_height > h * pixmapWidth:
            m = int((w - (pixmapWidth * h / pixmap_height)) / 2)
            self.setContentsMargins(m, 0, m, 0)
        else:
            m = int((h - (pixmap_height * w / pixmapWidth)) / 2)
            self.setContentsMargins(0, m, 0, m)
