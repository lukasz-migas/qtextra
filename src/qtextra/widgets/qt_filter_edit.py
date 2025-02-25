"""Filter edit."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QScrollArea, QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_tag import QtTagButton


class QtScrollableHLayout(QScrollArea):
    """Scrollable horizontal layout."""

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

    def add_widget(self, widget: QWidget, **kwargs: ty.Any) -> None:
        """Add widget."""
        self._main_layout.addWidget(widget, **kwargs)

    def insert_widget(self, index: int, widget: QWidget, **kwargs: ty.Any) -> None:
        """Insert widget."""
        self._main_layout.insertWidget(index, widget, **kwargs)

    def add_layout(self, layout: QWidget, **kwargs: ty.Any) -> None:
        """Add layout."""
        self._main_layout.addLayout(layout, **kwargs)

    def insert_layout(self, index: int, layout: QWidget, **kwargs: ty.Any) -> None:
        """Insert layout."""
        self._main_layout.insertLayout(index, layout, **kwargs)

    def remove_widget_or_layout(self, index: int) -> None:
        """Remove widget or layout based on index position."""
        item = self._main_layout.itemAt(index)
        if not item:
            return
        widget = item.widget()
        if widget:
            self._main_layout.removeWidget(widget)
            widget.deleteLater()


class QtFilterEdit(QWidget):
    """Scrollable edit.."""

    evt_filters_changed = Signal(list)

    def __init__(self, parent: QWidget | None = None, placeholder: str = "Type in...", above: bool = False):
        super().__init__(parent)

        self.text_edit = hp.make_line_edit(
            self,
            placeholder=placeholder,
            func_changed=self.emit_current_filters,
            func=self.on_add,
        )
        self._list_action = hp.make_action(
            self, "add", func=self.on_add, tooltip="Add currently entered text as a filter."
        )
        self.text_edit.addAction(self._list_action, self.text_edit.ActionPosition.TrailingPosition)

        self._scroll = QtScrollableHLayout(self)
        self._scroll.setMaximumHeight(self.text_edit.height())

        self._main_layout = hp.make_form_layout(margin=0)
        if above:
            self._main_layout.addRow(self._scroll)
            self._main_layout.addRow(self.text_edit)
        else:
            self._main_layout.addRow(self.text_edit)
            self._main_layout.addRow(self._scroll)
        self.setLayout(self._main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    def on_add(self) -> None:
        """Add filter."""
        text = self.text_edit.text()
        filters = self.get_filters()
        if not text or text in filters:
            return
        button = QtTagButton(text, text, allow_selected=False, action_type="delete", action_icon="cross")
        button.evt_action.connect(self.on_remove)
        self._scroll.insert_widget(self._scroll.count() - 1, button)
        self.evt_filters_changed.emit(self.get_filters())

    def on_remove(self, hash_id: str) -> None:
        """Remove filter."""
        filters = self.get_filters()
        index = filters.index(hash_id)
        self._scroll.remove_widget_or_layout(index)
        self.evt_filters_changed.emit(self.get_filters())

    def get_filters(self, current: bool = False) -> list[str]:
        """Get list of currently selected filters."""
        tags = []
        for i in range(self._scroll.count() - 1):
            widget: QtTagButton = self._scroll.widget().layout().itemAt(i).widget()
            tags.append(widget.tag)
        if current:
            text = self.text_edit.text()
            if text and text not in tags:
                tags.append(text)
        return tags

    def emit_current_filters(self) -> None:
        """Emit current filters."""
        self.evt_filters_changed.emit(self.get_filters(current=True))


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(horz=False)
    frame.setMinimumSize(600, 600)
    ha.addWidget(QtFilterEdit())
    ha.addWidget(QtFilterEdit())
    ha.addWidget(QtFilterEdit())

    frame.show()
    sys.exit(app.exec_())
