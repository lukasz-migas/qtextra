from __future__ import annotations

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLayout, QScrollArea, QSizePolicy, QWidget

import qtextra.helpers as hp


class QtScrollableHLayout(QScrollArea):
    """Scrollable horizontal layout."""

    MIN_HEIGHT: int = 30

    def __init__(self, parent: ty.Optional[QWidget] = None):
        super().__init__(parent)

        self._widget = QWidget()
        self._main_layout = hp.make_h_layout(stretch_after=True, spacing=1, margin=1, parent=self._widget)
        self.setWidgetResizable(True)
        self.setWidget(self._widget)
        self.setContentsMargins(0, 0, 0, 0)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    def count(self) -> int:
        """Return count of widgets."""
        return self._main_layout.count()

    def get_widget(self, index: int) -> QWidget | None:
        """Get widget at position."""
        item = self._main_layout.itemAt(index)
        if not item:
            return None
        widget = item.widget()
        return widget

    def addWidget(self, widget: QWidget, **kwargs: ty.Any) -> None:
        """Add widget."""
        self._main_layout.addWidget(widget, **kwargs)
        self._update_scroll()

    def insertWidget(self, index: int, widget: QWidget, **kwargs: ty.Any) -> None:
        """Insert widget."""
        self._main_layout.insertWidget(index, widget, **kwargs)
        self._update_scroll()

    def addLayout(self, layout: QLayout, **kwargs: ty.Any) -> None:
        """Add layout."""
        self._main_layout.addLayout(layout, **kwargs)
        self._update_scroll()

    def insertLayout(self, index: int, layout: QLayout, **kwargs: ty.Any) -> None:
        """Insert layout."""
        self._main_layout.insertLayout(index, layout, **kwargs)
        self._update_scroll()

    def removeWidgetOrLayout(self, index: int) -> None:
        """Remove widget or layout based on index position."""
        widget = self.get_widget(index)
        if widget:
            self._main_layout.removeWidget(widget)
            widget.deleteLater()
            self._update_scroll()

    def minimum_height_for_widgets(self) -> int:
        """Return minimum height for all widgets."""
        height = 0
        for i in range(self.count() - 1):
            widget = self.get_widget(i)
            if widget:
                height = max(height, widget.minimumHeight())
        return height

    def _update_scroll(self) -> None:
        height = self.MIN_HEIGHT
        if self.count() > 1:
            height = max(height, self.minimum_height_for_widgets())
        if self.maximumHeight() != height:
            self.setMaximumHeight(height + 8)
