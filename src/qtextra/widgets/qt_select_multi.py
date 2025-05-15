"""Multi-selection widget."""

from __future__ import annotations

import typing as ty

from natsort import natsorted
from qtpy.QtCore import QEvent, QObject, Qt, Signal
from qtpy.QtGui import QAction
from qtpy.QtWidgets import QFormLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtextra.widgets.qt_table_view_check import MultiColumnSingleValueProxyModel, QtCheckableTableView


def filter_selected(current_options: list[str], all_options: list[str]) -> list[str]:
    """Filter selected options."""
    return [option for option in current_options if option in all_options]


def format_options(options: list[str]) -> str:
    """Format options."""
    return "; ".join(options)


def unformat_options(options: str) -> list[str]:
    """Unformat options."""
    return [option.strip() for option in options.split(";") if option.strip()]


class SelectionWidget(QtFramelessPopup):
    """Selection widget."""

    TABLE_CONFIG = (
        TableConfig()  # type: ignore[no-untyped-call]
        .add("", "check", "bool", 25, no_sort=True, hidden=False, sizing="fixed")
        .add("option", "option", "str", 100, sizing="stretch")
    )

    # Signals
    evt_update = Signal(list)
    evt_changed = Signal(list)
    evt_temp_changed = Signal(list)

    cancel_clicked = False
    options: list[str] | None = None
    original_options: list[str] | None = None

    def __init__(self, parent: QWidget, title: str = "Select...", text: str = "", n_max: int = 0, min_width: int = 500):
        self.title = title
        self.text = text
        self.n_max = n_max
        super().__init__(parent)
        self.setMinimumWidth(min_width)
        self.setMinimumHeight(350)
        self.filter_by_option.setFocus()

    def set_options(self, options: list[str], selected_options: list[str] | None = None) -> None:
        """Set options."""
        if not selected_options:
            selected_options = []

        data = []
        selected_options_ = []
        for option in options:
            is_selected = option in selected_options
            data.append([is_selected, option])
            if is_selected:
                selected_options_.append(option)
        self.table.reset_data()
        self.table.add_data(data)
        self.options = selected_options_
        self.original_options = selected_options
        widths = [len(v) for v in options] or [50]
        if widths:
            self.setMinimumWidth(max([self.minimumWidth(), max(widths) * 10]))

    @property
    def selected_options(self) -> list[str]:
        """Return selected options."""
        indices = self.table.get_all_checked()
        self.options = [self.table.get_value(self.TABLE_CONFIG.option, index) for index in indices]
        return self.options

    def accept(self) -> None:
        """Return state."""
        # self.evt_changed.emit(self.selected_options)
        self.evt_update.emit(self.selected_options)
        super().accept()

    def on_cancel(self) -> None:
        """Return state."""
        self.cancel_clicked = True
        self.reject()

    def reject(self) -> None:
        """Return state."""
        if self.cancel_clicked:
            options = self.original_options
        else:
            options = self.selected_options
        self.evt_update.emit(options)
        super().reject()

    def on_check(self, index: int, _state: bool) -> None:
        """Check."""
        indices = self.table.get_all_checked()
        options = [self.table.get_value(self.TABLE_CONFIG.option, index) for index in indices]
        self.evt_temp_changed.emit(options)
        if self.n_max and len(indices) > self.n_max:
            other_index = next(i for i in indices if i != index)
            self.table.set_value(self.TABLE_CONFIG.check, other_index, False)

    def on_show_selected(self) -> None:
        """Show/hide selected."""
        self.table_proxy.setFilterByState(True, self.TABLE_CONFIG.check)

    def on_show_unselected(self) -> None:
        """Show/hide unselected."""
        self.table_proxy.setFilterByState(False, self.TABLE_CONFIG.check)

    def on_show_selected_clear(self) -> None:
        """Show/hide unselected."""
        self.table_proxy.setFilterByState(None, self.TABLE_CONFIG.check)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.table = QtCheckableTableView(self, config=self.TABLE_CONFIG, enable_all_check=True, sortable=True)
        self.table.setCornerButtonEnabled(False)
        self.table.evt_checked.connect(self.on_check)
        hp.set_font(self.table, THEMES.get_font_size())
        self.table.setup_model(
            self.TABLE_CONFIG.header, self.TABLE_CONFIG.no_sort_columns, self.TABLE_CONFIG.hidden_columns
        )
        self.table_proxy = MultiColumnSingleValueProxyModel(self)
        self.table_proxy.setSourceModel(self.table.model())
        self.table.model().table_proxy = self.table_proxy
        self.table.setModel(self.table_proxy)

        self.filter_by_option = hp.make_line_edit(
            self,
            placeholder="Filter by value...",
            func_changed=lambda text, col=self.TABLE_CONFIG.option: self.table_proxy.setFilterByColumn(text, col),
        )

        layout = hp.make_form_layout(parent=self, margin=6)

        if self.text:
            layout.addRow(
                hp.make_label(
                    self,
                    self.text,
                    alignment=Qt.AlignmentFlag.AlignHCenter,
                    wrap=True,
                    enable_url=True,
                )
            )
        layout.addRow(self.table)
        layout.addRow(
            hp.make_h_layout(
                hp.make_qta_btn(self, "visible_on", func=self.on_show_selected, tooltip="Only show checked items."),
                hp.make_qta_btn(
                    self, "visible_off", func=self.on_show_unselected, tooltip="Only show unchecked items."
                ),
                hp.make_qta_btn(self, "clear", func=self.on_show_selected_clear, tooltip="Clear checked filter."),
                self.filter_by_option,
                stretch_id=(3,),
                spacing=2,
            )
        )
        layout.addRow(
            hp.make_h_layout(
                hp.make_btn(self, "OK", func=self.accept), hp.make_btn(self, "Cancel", func=self.on_cancel)
            )
        )
        return layout


class QtMultiSelect(QWidget):
    """Multi select widget."""

    editingFinished = Signal()
    textChanged = Signal(str)
    evt_selection_changed = Signal(list)

    def __init__(
        self,
        parent: QWidget,
        allow_clear: bool = False,
        instant_set: bool = False,
        n_max: int = 0,
        hover_opens: bool = False,
    ):
        self.instant_set = instant_set
        self.n_max = n_max
        self.hover_opens = hover_opens

        super().__init__(parent)
        self.options: list[str] = []
        self.selected_options: list[str] = []
        self.text_edit = hp.make_line_edit(self, placeholder="Select...")
        self.text_edit.setReadOnly(True)
        self.text_edit.setClearButtonEnabled(allow_clear)
        self.text_edit.installEventFilter(self)

        self._clear_action = self.text_edit.findChild(QAction)
        if self._clear_action:
            self._clear_action.setEnabled(True)
            self._clear_action.triggered.connect(self.clear_current)

        self._list_action = hp.make_action(
            self, "list", func=self.on_select, tooltip="Click here to select one or more options"
        )
        self.text_edit.addAction(self._list_action, self.text_edit.ActionPosition.LeadingPosition)

        layout = hp.make_h_layout(self.text_edit, stretch_id=0, spacing=0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.text_edit.editingFinished.connect(self.editingFinished.emit)
        self.text_edit.textChanged.connect(self.textChanged.emit)

    def enterEvent(self, event: ty.Any) -> None:
        """Enter event."""
        if self.hover_opens:
            self.text_edit.setFocus()
        super().enterEvent(event)

    def eventFilter(self, obj: QObject, evt: QEvent) -> bool:
        """Event filter."""
        if self.isEnabled() and obj == self.text_edit and evt.type() == QEvent.Type.MouseButtonPress:  # type: ignore
            self.on_select()
            return True
        return super().eventFilter(obj, evt)

    @classmethod
    def from_schema(
        cls: type[QtMultiSelect],
        parent: QWidget,
        description: str = "",
        options: list[str] | None = None,
        value: str = "",
        default: str = "",
        placeholder: str = "Select...",
        func: ty.Callable | ty.Sequence[ty.Callable] | None = None,
        func_changed: ty.Callable | ty.Sequence[ty.Callable] | None = None,
        items: dict[str, ty.Any] | None = None,
        n_max: int = 0,
        sort: bool = False,
        **_kwargs: ty.Any,
    ) -> QtMultiSelect:
        """Init."""
        if default:
            value = default
        if value is None:
            value = default
        if items and "enum" in items:
            options = items["enum"]
        if isinstance(value, str):
            values = value.split(";") if value else []
        else:
            values = value

        if sort:
            options = natsorted(options) if options else []

        obj = cls(parent, n_max=n_max)
        obj.text_edit.setPlaceholderText(placeholder)
        obj.options = options or []
        obj.selected_options = values
        obj.text_edit.setText(format_options(obj.selected_options))
        obj.setToolTip(description)
        obj.text_edit.setToolTip(description)
        if func:
            [obj.editingFinished.connect(func_) for func_ in hp._validate_func(func)]
        if func_changed:
            [obj.textChanged.connect(func_) for func_ in hp._validate_func(func_changed)]
        return obj

    def polish(self) -> None:
        """Polish widget."""
        hp.polish_widget(self, self.text_edit)

    def setObjectName(self, name: str) -> None:  # type: ignore
        """Set object name."""
        self.text_edit.setObjectName(name)
        super().setObjectName(name)

    def currentOptions(self) -> list[str]:
        """Return current options."""
        return self.options

    def clear_current(self) -> None:
        """Clear selection."""
        self.selected_options = []
        self.text_edit.setText("")
        self.evt_selection_changed.emit(self.selected_options)

    def clear(self) -> None:
        """Clear selection."""
        self.text_edit.setText("")
        self.selected_options = []
        self.options = []

    def toggle_clear_action(self) -> None:
        """Toggle visibility of clear action."""
        if not self.text_edit.isClearButtonEnabled():
            return
        text = self.text_edit.text()
        self._clear_action.setVisible(text != "")

    def set_options(self, options: list[str], selected_options: list[str] | None = None) -> None:
        """List of options."""
        if selected_options is None:
            selected_options = []
        selected_options = filter_selected(selected_options, options)
        self.options = options
        self.selected_options = selected_options
        self.text_edit.setText(format_options(selected_options))

    def set_selected_options(self, selected_options: list[str]) -> None:
        """List of options."""
        if selected_options is None:
            selected_options = []
        if not isinstance(selected_options, list):
            selected_options = [selected_options]
        selected_options = list(map(str, selected_options))
        if self.options:
            selected_options = filter_selected(selected_options, self.options)
        self.selected_options = selected_options
        self.text_edit.setText(format_options(selected_options))
        self.toggle_clear_action()

    def _set_selected_options(self, selected_options: list[str]) -> None:
        """List of options."""
        if not selected_options:
            selected_options = []
        self.selected_options = selected_options
        self.text_edit.setText(format_options(selected_options))
        # trigger update events
        self.textChanged.emit(format_options(selected_options))
        self.editingFinished.emit()
        self.evt_selection_changed.emit(selected_options)
        self.toggle_clear_action()

    def set_selected_options_temp(self, selected_options: list[str]) -> None:
        """List of options."""
        with hp.qt_signals_blocked(self.text_edit):
            self.set_selected_options(selected_options)
            self.toggle_clear_action()

    def on_select(self) -> None:
        """Select."""
        dlg = SelectionWidget(self, n_max=self.n_max, min_width=self.text_edit.width())
        dlg.set_options(self.options, self.selected_options)
        dlg.filter_by_option.setFocus()
        dlg.evt_temp_changed.connect(self._set_selected_options if self.instant_set else self.set_selected_options_temp)
        dlg.evt_update.connect(self._set_selected_options)
        dlg.show_below_widget(self, x_offset=0, y_offset=0)

    def get_checked(self) -> list[str]:
        """Return list of checked values."""
        return self.selected_options


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)

    wdg = QtMultiSelect(frame)
    wdg.set_options(["option1", "option2", "option3"], ["option1", "option3"])
    ha.addWidget(wdg)
    wdg = QtMultiSelect(frame, allow_clear=True)
    wdg.set_options(["option1", "option2", "option3"], ["option1", "option3"])
    ha.addWidget(wdg)

    frame.show()
    sys.exit(app.exec_())
