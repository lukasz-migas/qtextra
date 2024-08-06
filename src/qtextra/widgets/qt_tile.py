from __future__ import annotations

import typing as ty

from pydantic import BaseModel, Field, validator
from qtpy.QtCore import Qt
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QFrame, QVBoxLayout, QWidget

import qtextra.helpers as hp


class Tile(BaseModel):
    """Workflow model."""

    title: str
    description: str
    icon: ty.Optional[str] = ""
    func: ty.Optional[ty.Callable] = None
    icon_kws: ty.Optional[ty.Dict[str, ty.Any]] = None
    warning: str = ""

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    @validator("func", pre=True)
    def _validate_widget(cls, value) -> func:
        """Check correct model is provided."""
        if not value:
            return lambda: None
        if not callable(value):
            raise ValueError("Widget class must have a run method.")
        return value


class QtTileWidget(QFrame):
    """Widget to display workflow."""

    def __init__(self, parent: QWidget, tile: Tile):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFixedSize(250, 250)
        self.setFrameShape(QFrame.Shape.Box)

        self._tile = tile
        # layout: Title, image, description
        self._title = hp.make_label(
            self, self._tile.title, wrap=True, alignment=Qt.AlignmentFlag.AlignHCenter, object_name="large_text"
        )
        self._title.adjustSize()
        if self._tile.icon:
            self._image = hp.make_qta_label(self, self._tile.icon, **(self._tile.icon_kws or {}))
            self._image.set_xxxlarge()
        else:
            self._image = hp.make_label(self, "")  # type: ignore[assignment]
        self._description = hp.make_label(
            self, self._tile.description, wrap=True, alignment=Qt.AlignmentFlag.AlignHCenter, object_name="medium_text"
        )
        self._warning = hp.make_label(
            self, self._tile.warning, wrap=True, alignment=Qt.AlignmentFlag.AlignHCenter, object_name="small_text"
        )
        if not self._tile.warning:
            self._warning.hide()

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._title, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)
        layout.addWidget(self._image, stretch=2, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._description, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)
        layout.addWidget(self._warning, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Handle mouse press event."""
        self._tile.func()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Handle mouse release event."""
        return super().mouseReleaseEvent(event)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe()
        frame.setMinimumSize(400, 400)

        model = Tile(
            title="One-vs-One",
            description="Compare intensity of one ion to another.",
            func=lambda: print("Hello"),
            icon="mdi.chart-scatter-plot",
        )
        widget = QtTileWidget(frame, model)
        ha.addWidget(widget)
        widget = QtTileWidget(frame, model)
        ha.addWidget(widget)
        model = Tile(
            title="One-vs-One",
            description="Compare intensity of one ion to another.",
            func=lambda: print("Hello"),
            icon="mdi.chart-scatter-plot",
            icon_kws={"color": "#ff0000"},
        )
        widget = QtTileWidget(frame, model)
        ha.addWidget(widget)
        frame.show()
        sys.exit(app.exec_())

    _main()  # type: ignore[no-untyped-call]
