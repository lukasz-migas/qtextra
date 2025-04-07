"""Scrollable label."""

from __future__ import annotations

import typing as ty

from koyo.typing import PathLike
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QLabel, QScrollArea, QWidget


class QtScrollableLabel(QScrollArea):
    """Scrollable label."""

    evt_clicked = Signal()

    def __init__(
        self,
        parent: ty.Optional[QWidget] = None,
        text: ty.Optional[str] = None,
        image_path: ty.Optional[PathLike] = None,
        wrap: bool = False,
    ):
        super().__init__(parent)

        self.label = QLabel()
        self.label.setWordWrap(wrap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        if text:
            self.setText(text)
        elif image_path:
            self.set_image(image_path)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWidgetResizable(True)
        self.setWidget(self.label)
        self.setContentsMargins(0, 0, 0, 0)

    def setText(self, text: str) -> None:
        """Set label text."""
        self.label.setText(text)

    def set_image(self, image_path: PathLike) -> None:
        """Set image."""
        pixmap = QPixmap(str(image_path))
        self.label.setPixmap(pixmap)
        self.label.adjustSize()

    def clear(self) -> None:
        """Clear label."""
        self.label.clear()

    def mousePressEvent(self, event) -> None:
        """Mouse press event."""
        self.evt_clicked.emit()
        return super().mousePressEvent(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)

    ha.addWidget(QLabel("Scrollable label without wrap"))
    wdg = QtScrollableLabel(text="This is a long text that will make the QLabel scrollable. " * 20)
    ha.addWidget(wdg)
    ha.addWidget(QLabel("Scrollable label with wrap"))
    wdg = QtScrollableLabel(text="This is a long text that will make the QLabel scrollable. " * 20, wrap=True)
    ha.addWidget(wdg)

    frame.show()
    sys.exit(app.exec_())
