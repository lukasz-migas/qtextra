"""Multi-selection widget."""
from __future__ import annotations

import typing as ty

from qtpy.QtCore import QEvent, QObject, Signal
from qtpy.QtWidgets import QFormLayout, QWidget

import qtextra.helpers as hp
from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_dialog import QtFramelessTool
from qtextra.widgets.qt_table_view import FilterProxyModel, QtCheckableTableView


def filter_selected(current_options: list[str], all_options: list[str]) -> list[str]:
    """Filter selected options."""
    return [option for option in current_options if option in all_options]


def format_options(options: list[str]) -> str:
    """Format options."""
    return "; ".join(options)


def unformat_options(options: str) -> list[str]:
    """Unformat options."""
    return [option.strip() for option in options.split(";") if option.strip()]


class SelectionWidget(QtFramelessTool):
    """Selection widget."""

    evt_changed = Signal(list)
    evt_temp_changed = Signal(list)
    TABLE_CONFIG = (
        TableConfig()  # type: ignore[no-untyped-call]
        .add("", "check", "bool", 25, no_sort=True, hidden=False, sizing="fixed")
        .add("option", "option", "str", 100, sizing="stretch")
    )

    options: list[str] | None = None
    original_options: list[str] | None = None

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setMinimumWidth(350)
        self.setMinimumHeight(350)
        self.filter_by_option.setFocus()

    def set_options(self, options: list[str], selected_options: list[str]) -> None:
        """Set options."""
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

    def accept(self) -> None:
        """Return state."""
        indices = self.table.get_all_checked()
        self.options = [self.table.get_value(self.TABLE_CONFIG.option, index) for index in indices]
        return super().accept()

    def reject(self) -> None:
        """Return state."""
        self.evt_changed.emit(self.original_options)
        return super().reject()

    def on_check(self, _index: int, _state: bool) -> None:
        """Check."""
        indices = self.table.get_all_checked()
        options = [self.table.get_value(self.TABLE_CONFIG.option, index) for index in indices]
        self.evt_temp_changed.emit(options)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        _, header_layout = self._make_hide_handle("Select...")

        self.table = QtCheckableTableView(self, config=self.TABLE_CONFIG, enable_all_check=True, sortable=True)
        self.table.setCornerButtonEnabled(False)
        self.table.evt_checked.connect(self.on_check)
        hp.set_font(self.table)
        self.table.setup_model(
            self.TABLE_CONFIG.header, self.TABLE_CONFIG.no_sort_columns, self.TABLE_CONFIG.hidden_columns
        )
        self.table_proxy = FilterProxyModel(self)
        self.table_proxy.setSourceModel(self.table.model())
        self.table.model().table_proxy = self.table_proxy
        self.table.setModel(self.table_proxy)
        self.filter_by_option = hp.make_line_edit(
            self,
            placeholder="Type in option value...",
            func_changed=lambda text, col=self.TABLE_CONFIG.option: self.table_proxy.setFilterByColumn(text, col),
        )

        layout = hp.make_form_layout(self)
        hp.style_form_layout(layout)
        layout.addRow(header_layout)
        layout.addRow(self.filter_by_option)
        layout.addRow(self.table)
        layout.addRow(
            hp.make_h_layout(hp.make_btn(self, "OK", func=self.accept), hp.make_btn(self, "Cancel", func=self.reject))
        )
        return layout


class QtMultiSelect(QWidget):
    """Multi select widget."""

    editingFinished = Signal()
    textChanged = Signal(str)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.options: list[str] = []
        self.selected_options: list[str] = []
        self.text_edit = hp.make_line_edit(self, placeholder="Select...")
        self.text_edit.setReadOnly(True)
        self.text_edit.setClearButtonEnabled(False)
        self.text_edit.installEventFilter(self)
        self.select_btn = hp.make_qta_btn(
            self, "select", func=self.on_select, tooltip="Click here to select one or more options..."
        )

        layout = hp.make_h_layout(self.text_edit, self.select_btn, stretch_id=0, spacing=0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.text_edit.editingFinished.connect(self.editingFinished.emit)
        self.text_edit.textChanged.connect(self.textChanged.emit)

    def eventFilter(self, obj: QObject, evt: QEvent) -> bool:
        """Event filter."""
        if self.isEnabled() and obj == self.text_edit and evt.type() == QEvent.MouseButtonPress:  # type: ignore
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
        show_btn: bool = True,
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
        obj = cls(parent)
        obj.text_edit.setPlaceholderText(placeholder)
        obj.options = options or []
        obj.selected_options = values
        obj.text_edit.setText(format_options(obj.selected_options))
        obj.setToolTip(description)
        obj.text_edit.setToolTip(description)
        if not show_btn:
            obj.select_btn.hide()
        if func:
            [obj.editingFinished.connect(func_) for func_ in hp._validate_func(func)]
        if func_changed:
            [obj.textChanged.connect(func_) for func_ in hp._validate_func(func_changed)]
        return obj

    def polish(self) -> None:
        """Polish widget."""
        hp.polish_widget(self)
        hp.polish_widget(self.text_edit)
        hp.polish_widget(self.select_btn)

    def setObjectName(self, name: str) -> None:  # type: ignore
        """Set object name."""
        self.text_edit.setObjectName(name)
        super().setObjectName(name)

    def currenOptions(self) -> list[str]:
        """Return current options."""
        return self.options

    def clear(self) -> None:
        """Clear selection."""
        self.text_edit.setText("")
        self.selected_options = []
        self.options = []

    def set_options(self, options: list[str], selected_options: list[str]) -> None:
        """List of options."""
        selected_options = filter_selected(selected_options, options)
        self.options = options
        self.selected_options = selected_options
        self.text_edit.setText(format_options(selected_options))

    def set_selected_options(self, selected_options: list[str]) -> None:
        """List of options."""
        if selected_options is None:
            selected_options = []
        if self.options:
            selected_options = filter_selected(selected_options, self.options)
        self.selected_options = selected_options
        self.text_edit.setText(format_options(selected_options))

    def set_selected_options_temp(self, selected_options: list[str]) -> None:
        """List of options."""
        with hp.qt_signals_blocked(self.text_edit):
            self.set_selected_options(selected_options)

    def on_select(self) -> None:
        """Select."""
        dlg = SelectionWidget(self)
        dlg.set_options(self.options, self.selected_options)
        dlg.evt_changed.connect(self.set_selected_options)
        dlg.evt_temp_changed.connect(self.set_selected_options_temp)
        if bool(dlg.exec()):
            selected_options = dlg.options
            if not selected_options:
                selected_options = []
            self.selected_options = selected_options
            self.text_edit.setText(format_options(selected_options))
            # trigger update events
            self.textChanged.emit(format_options(selected_options))
            self.editingFinished.emit()

    def get_checked(self) -> list[str]:
        """Return list of checked values."""
        return self.selected_options
