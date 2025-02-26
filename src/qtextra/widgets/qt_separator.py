"""Horizontal and Vertical lines."""

from qtpy.QtWidgets import QFrame, QWidget


class QtHorzLine(QFrame):
    """Horizontal line."""

    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)


class QtVertLine(QFrame):
    """Vertical line."""

    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
