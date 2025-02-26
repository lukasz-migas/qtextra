"""Filter edit."""

from __future__ import annotations

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_tag import QtTagButton
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayout


class QtFilterEdit(QWidget):
    """Scrollable edit.."""

    evt_filters_changed = Signal(list)

    def __init__(
        self, parent: QWidget | None = None, placeholder: str = "Type in...", above: bool = False, flow: bool = False
    ):
        super().__init__(parent)

        self.text_edit = hp.make_line_edit(
            self, placeholder=placeholder, func_changed=self.emit_current_filters, func=self.on_add
        )
        self.clear_action = hp.make_action(self, "clear", func=self.on_remove_all, tooltip="Remove all filters.")
        self.text_edit.addAction(self.clear_action, self.text_edit.ActionPosition.TrailingPosition)
        self.add_action = hp.make_action(
            self, "add", func=self.on_add_action, tooltip="Add currently entered text as a filter."
        )
        self.text_edit.addAction(self.add_action, self.text_edit.ActionPosition.TrailingPosition)

        if flow:
            self._filter_layout = hp.make_flow_layout(margin=0, horizontal_spacing=1, vertical_spacing=1)
        else:
            self._filter_layout = QtScrollableHLayout(self)
            self._filter_layout.MIN_HEIGHT = self.text_edit.height()
        self._n = self._filter_layout.count()

        self._main_layout = hp.make_form_layout(margin=0)
        if above:
            self._main_layout.addRow(self._filter_layout)
            self._main_layout.addRow(self.text_edit)
        else:
            self._main_layout.addRow(self.text_edit)
            self._main_layout.addRow(self._filter_layout)
        self.setLayout(self._main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    def on_add_action(self) -> None:
        """This is a workaround some minor issues with action being triggered twice."""
        with hp.qt_signals_blocked(self.text_edit):
            self.on_add()

    def on_add(self) -> None:
        """Add filter."""
        text = self.text_edit.text()
        filters = self.get_filters()
        if not text or text in filters:
            return
        button = QtTagButton(text, text, allow_selected=False, action_type="delete", action_icon="cross")
        button.evt_action.connect(self.on_remove)
        self._filter_layout.insertWidget(self._filter_layout.count() - 1, button)
        self.evt_filters_changed.emit(self.get_filters())

    def on_remove(self, hash_id: str) -> None:
        """Remove filter."""
        filters = self.get_filters()
        index = filters.index(hash_id)
        self._filter_layout.removeWidgetOrLayout(index)
        self.evt_filters_changed.emit(self.get_filters())

    def on_remove_all(self) -> None:
        """Remove all filters."""
        while self._filter_layout.count() != self._n:
            self._filter_layout.removeWidgetOrLayout(0)
        self.evt_filters_changed.emit([])

    def get_filters(self, current: bool = False) -> list[str]:
        """Get list of currently selected filters."""
        tags = []
        for i in range(self._filter_layout.count() - self._n):
            widget = self._filter_layout.get_widget(i)
            if widget:
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
    ha.addWidget(QtFilterEdit(above=True))
    ha.addWidget(QtFilterEdit(flow=True))

    frame.show()
    sys.exit(app.exec_())
