"""Filter edit."""

from __future__ import annotations

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_icon import QtAndOrButton
from qtextra.widgets.qt_button_tag import QtTagButton
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayoutWidget


class QtFilterEdit(QWidget):
    """Scrollable edit.."""

    evt_filters_changed = Signal(list, str)

    def __init__(
        self,
        parent: QWidget | None = None,
        placeholder: str = "Type in...",
        above: bool = False,
        flow: bool = False,
        enable_switch: bool = False,
    ):
        self.enable_switch = enable_switch
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

        self.switch_toggle = QtAndOrButton(auto_connect=True, state=True)
        self.switch_toggle.set_normal()
        self.switch_toggle.evt_toggled.connect(self.emit_current_filters)
        if not enable_switch:
            self.switch_toggle.hide()

        if flow:
            self._filter_layout = hp.make_flow_layout(margin=0, horizontal_spacing=1, vertical_spacing=1)
        else:
            self._filter_layout = QtScrollableHLayoutWidget(self)
            self._filter_layout.set_min_height(self.text_edit.height())
        self._n = self._filter_layout.count()

        self._main_layout = hp.make_form_layout(margin=0)
        if above:
            self._main_layout.addRow(self._filter_layout)
            self._main_layout.addRow(
                hp.make_h_layout(self.text_edit, self.switch_toggle, spacing=1, margin=0, stretch_id=(0,))
            )
        else:
            self._main_layout.addRow(
                hp.make_h_layout(self.text_edit, self.switch_toggle, spacing=1, margin=0, stretch_id=(0,))
            )
            self._main_layout.addRow(self._filter_layout)
        self.setLayout(self._main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

    def on_add_action(self) -> None:
        """This is a workaround some minor issues with action being triggered twice."""
        with hp.qt_signals_blocked(self.text_edit):
            self.on_add()

    def on_add(self) -> None:
        """Add filter."""
        text = self.text_edit.text()
        self.add_filter(text)

    def add_filter(self, text: str) -> None:
        """Add filter."""
        filters = self.get_filters()
        if not text or text in filters:
            return
        button = QtTagButton(text, text, allow_selected=False, action_type="delete", action_icon="cross")
        button.evt_action.connect(self.on_remove)
        button.evt_clicked.connect(self.on_update)
        self._filter_layout.insertWidget(0, button)
        self.evt_filters_changed.emit(self.get_filters(), self.mode)
        self.text_edit.setText("")

    def on_update(self, text: str) -> None:
        """Update filter."""
        self.text_edit.setText(text)
        self.text_edit.setFocus()
        self.on_remove(text)

    def on_remove(self, text: str) -> None:
        """Remove filter."""
        filters = self.get_filters()
        index = filters.index(text)
        self._filter_layout.removeWidgetOrLayout(index)
        self.evt_filters_changed.emit(self.get_filters(), self.mode)

    def on_remove_all(self) -> None:
        """Remove all filters."""
        while self._filter_layout.count() != self._n:
            self._filter_layout.removeWidgetOrLayout(0)
        self.evt_filters_changed.emit([], self.mode)

    def get_filters(self, current: bool = False) -> list[str]:
        """Get list of currently selected filters."""
        tags = []
        for i in range(self._filter_layout.count() - self._n):
            widget = self._filter_layout.get_widget(i)
            if widget:
                tags.append(widget.text)
        if current:
            text = self.text_edit.text()
            if text and text not in tags:
                tags.append(text)
        return tags

    @property
    def mode(self) -> str | None:
        """Get mode."""
        if not self.enable_switch:
            return None
        return "AND" if self.switch_toggle.state else "OR"

    def emit_current_filters(self) -> None:
        """Emit current filters."""
        self.evt_filters_changed.emit(self.get_filters(current=True), self.mode)

    # Alias methods to offer Qt-like interface
    getFilters = get_filters
    addFilter = add_filter
    onAdd = on_add
    onRemove = on_remove
    onRemoveAll = on_remove_all
    emitCurrentFilters = emit_current_filters


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(horz=False)
    frame.setMinimumSize(600, 600)
    ha.addWidget(QtFilterEdit())
    ha.addWidget(QtFilterEdit(above=True))
    ha.addWidget(QtFilterEdit(flow=True))
    ha.addWidget(QtFilterEdit(enable_switch=True))

    frame.show()
    sys.exit(app.exec_())
