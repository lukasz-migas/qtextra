from __future__ import annotations

import typing as ty

from qtpy.QtCore import QEvent, Signal
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QStyle, QStyleOption, QWidget

from qtextra import helpers as hp


class QtDragWidget(QWidget):
    """Drag widget."""

    evt_dropped = Signal("QEvent")

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self.setAutoFillBackground(True)
        self.setAcceptDrops(True)

    def _update_property(self, prop: str, value: bool) -> None:
        """Update properties of widget to update style."""
        self.setProperty(prop, value)
        hp.polish_widget(self)

    def dragEnterEvent(self, event: QEvent) -> None:
        """Override Qt method.

        Provide style updates on event.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._update_property("drag", True)
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Override Qt method.

        Provide style updates on event.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._update_property("drag", False)

    def dropEvent(self, event):
        """Override Qt method.

        Provide style updates on event and emit the drop event.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self._update_property("drag", False)
        self.evt_dropped.emit(event)

    def paintEvent(self, event):
        """Override Qt method.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        option = QStyleOption()
        option.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, p, self)
