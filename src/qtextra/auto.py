"""Helpers for generating Qt widgets from lightweight schema dictionaries."""

from __future__ import annotations

import typing as ty

from loguru import logger
from qtpy import QtWidgets as Qw
from qtpy.QtCore import Qt

import qtextra.helpers as qp
from qtextra.typing import OptionalCallback

if ty.TYPE_CHECKING:
    from qtextra.widgets.qt_select_multi import QtMultiSelect
    from qtextra.widgets.qt_toggle_group import QtToggleGroup

WidgetValue = str | int | float | bool | None | list[str]
WidgetOrLayout = Qw.QWidget | Qw.QLayout


def set_values_from_dict(
    data: dict[str, WidgetValue],
    widgets: dict[str, Qw.QWidget],
    block: bool = True,
) -> None:
    """Populate widgets from a mapping of names to values."""
    for key, value in data.items():
        try:
            widget = widgets[key]
        except KeyError:
            logger.error(f"Could not find widget for {key}")
            continue

        with qp.qt_signals_blocked(widget, block_signals=block):
            set_value_to_widget(widget, value)


def _append_widgets(
    widget: Qw.QWidget,
    layout: Qw.QFormLayout,
    widgets: tuple[Qw.QWidget, ...] | None,
    label: str | None = None,
    search_widget: Qw.QWidget | None = None,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    """Append one or more widgets to a form layout, optionally after a row anchor."""
    if not widgets:
        raise ValueError("No widgets provided")

    new_layout = qp.make_h_layout(*widgets, spacing=1, alignment=Qt.AlignmentFlag.AlignVCenter)
    row = _get_insertion_row(layout, search_widget)
    _insert_form_row(layout, row, new_layout, label=label, parent=widget)
    return widget, layout


def _add_widget(
    parent: Qw.QWidget,
    widget: Qw.QWidget,
    layout: Qw.QFormLayout,
    func: ty.Callable,
    label: str,
    icon: str = "help",
    tooltip: str = "Learn more...",
    extras: tuple[Qw.QWidget, ...] | None = None,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    """Attach a button plus optional extras to an existing form row."""
    if extras is None:
        extras = ()
    return _add_widgets(
        widget,
        layout,
        label,
        widgets=(qp.make_qta_btn(parent, icon, average=True, func=func, tooltip=tooltip), *extras),
    )


def _add_widgets(
    widget: Qw.QWidget,
    layout: Qw.QFormLayout,
    label: str,
    widgets: tuple[Qw.QWidget, ...] | None = None,
    before_widgets: tuple[Qw.QWidget, ...] | None = None,
    spacing: int = 1,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    """Attach extra widgets before or after an existing form field."""
    trailing_widgets = widgets or ()
    leading_widgets = before_widgets or ()
    if not trailing_widgets and not leading_widgets:
        raise ValueError("No widgets provided")

    row, db_label, db_widget = qp.remove_widget_in_form_layout(layout, label)
    if row is None or db_label is None or db_widget is None:
        return widget, layout

    if isinstance(db_widget, Qw.QHBoxLayout):
        new_layout = db_widget
        for extra_widget in trailing_widgets:
            new_layout.addWidget(extra_widget)
        for extra_widget in reversed(leading_widgets):
            new_layout.insertWidget(0, extra_widget)
    else:
        new_layout = qp.make_h_layout(
            *leading_widgets,
            db_widget,
            *trailing_widgets,
            stretch_id=len(leading_widgets),
            spacing=spacing,
        )
    qp.insert_widget_in_form_layout(layout, row, db_label, new_layout)
    return widget, layout


def _insert_before_widget(
    widget: Qw.QWidget,
    layout: Qw.QFormLayout,
    label: str,
    label_widget: Qw.QWidget | None,
    widget_widget: WidgetOrLayout,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    """Insert a row before an existing labeled row."""
    row = qp.find_row_for_label_in_form_layout(layout, label)
    if row is not None:
        if label_widget is None:
            layout.insertRow(row, widget_widget)
        else:
            layout.insertRow(row, label_widget, widget_widget)
    return widget, layout


def _insert_after_widget(
    widget: Qw.QWidget,
    layout: Qw.QFormLayout,
    label: str,
    label_widget: Qw.QWidget | None,
    widget_widget: WidgetOrLayout,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    """Insert a row after an existing labeled row."""
    row = qp.find_row_for_label_in_form_layout(layout, label)
    if row is not None:
        if label_widget is None:
            layout.insertRow(row + 1, widget_widget)
        else:
            layout.insertRow(row + 1, label_widget, widget_widget)
    return widget, layout


def _get_insertion_row(layout: Qw.QFormLayout, search_widget: Qw.QWidget | None) -> int | None:
    """Return the row after ``search_widget``, when present."""
    if search_widget is None:
        return None
    row = qp.find_row_for_widget(layout, search_widget)
    if row is None:
        return None
    return row + 1


def _insert_form_row(
    layout: Qw.QFormLayout,
    row: int | None,
    widget_or_layout: WidgetOrLayout,
    *,
    label: str | None = None,
    parent: Qw.QWidget | None = None,
) -> None:
    """Insert or append a row in a form layout."""
    label_widget = qp.make_label(parent, label) if label else None
    if row is None:
        if label_widget is None:
            layout.addRow(widget_or_layout)
        else:
            layout.addRow(label_widget, widget_or_layout)
        return
    if label_widget is None:
        layout.insertRow(row, widget_or_layout)
    else:
        layout.insertRow(row, label_widget, widget_or_layout)


def guess_widget_cls(schema: dict[str, ty.Any]) -> str:
    """Guess an appropriate widget class from a JSON-schema-like field definition."""
    item_type = _extract_schema_type(schema)
    if item_type == "array":
        return "multi_combo_box" if schema.get("enum") else "line_edit"
    if item_type == "string":
        return "combo_box" if schema.get("enum") else "line_edit"
    if item_type == "boolean":
        return "checkbox"
    if item_type == "integer":
        return "int_spin_box"
    if item_type == "number":
        return "double_spin_box"
    raise ValueError(f"Could not parse '{item_type}'")


def _extract_schema_type(schema: dict[str, ty.Any]) -> str:
    """Extract the schema type from ``type`` or the first ``anyOf`` entry."""
    item_type = schema.get("type")
    if item_type:
        return item_type

    any_of = schema.get("anyOf")
    if any_of:
        first = any_of[0]
        if isinstance(first, dict) and "type" in first:
            return first["type"]

    raise ValueError("Schema must define either 'type' or 'anyOf'.")


def _resolve_widget_cls(schema: dict[str, ty.Any]) -> str:
    """Resolve ``widget_cls`` from schema, allowing tuple annotations."""
    widget_cls = schema.get("widget_cls")
    if widget_cls is None:
        return guess_widget_cls(schema)
    if isinstance(widget_cls, tuple):
        return widget_cls[0]
    return widget_cls


def _make_widget(
    parent: Qw.QWidget,
    widget_cls: str,
    schema: dict[str, ty.Any],
    func: OptionalCallback = None,
) -> Qw.QWidget:
    """Instantiate a widget for a schema field."""

    def make_line_edit() -> Qw.QWidget:
        return qp.make_line_edit(parent, func=func, func_clear=func, **schema)

    def make_line_edit_changed() -> Qw.QWidget:
        return qp.make_line_edit(parent, func_changed=func, func_clear=func, **schema)

    def make_disabled_line_edit() -> Qw.QWidget:
        return qp.make_line_edit(parent, func=func, disabled=True, **schema)

    def make_disabled_line_edit_changed() -> Qw.QWidget:
        return qp.make_line_edit(parent, func_changed=func, disabled=True, **schema)

    def make_disabled_label() -> Qw.QWidget:
        return qp.make_label(parent, disabled=True, **schema)

    def make_checkbox() -> Qw.QWidget:
        return qp.make_checkbox(parent, "", func=func, **schema)

    def make_checkbox_with_text() -> Qw.QWidget:
        return qp.make_checkbox(parent, schema.get("title", ""), func=func, **schema)

    def make_int_spin_box() -> Qw.QWidget:
        return qp.make_int_spin_box(parent, func=func, **schema)

    def make_double_spin_box() -> Qw.QWidget:
        return qp.make_double_spin_box(parent, func=func, **schema)

    def make_combo_box() -> Qw.QWidget:
        return qp.make_combobox(parent, func=func, **schema)

    def make_searchable_combo_box() -> Qw.QWidget:
        return qp.make_searchable_combobox(parent, func_index=func, **schema)

    def make_multi_combo_box() -> Qw.QWidget:
        return qp.make_checkable_combobox(parent, func=func, **schema)

    def make_multi_select() -> Qw.QWidget:
        return _make_multi_select(parent, schema, func=func, n_max=0)

    def make_single_select() -> Qw.QWidget:
        return _make_multi_select(parent, schema, func=func, n_max=1)

    def make_single_toggle() -> Qw.QWidget:
        return _make_toggle_group(parent, schema, func=func)

    def make_single_toggle_multiline() -> Qw.QWidget:
        return _make_toggle_group(parent, schema, func=func, multiline=True)

    def make_multi_toggle() -> Qw.QWidget:
        return _make_toggle_group(parent, schema, func=func, exclusive=False)

    factories: dict[str, ty.Callable[[], Qw.QWidget]] = {
        "line_edit": make_line_edit,
        "line_edit_changed": make_line_edit_changed,
        "disabled_line_edit": make_disabled_line_edit,
        "disabled_line_edit_changed": make_disabled_line_edit_changed,
        "disabled_label": make_disabled_label,
        "checkbox": make_checkbox,
        "checkbox_with_text": make_checkbox_with_text,
        "int_spin_box": make_int_spin_box,
        "double_spin_box": make_double_spin_box,
        "combo_box": make_combo_box,
        "searchable_combo_box": make_searchable_combo_box,
        "multi_combo_box": make_multi_combo_box,
        "multi_select": make_multi_select,
        "single_select": make_single_select,
        "single_toggle": make_single_toggle,
        "single_toggle_multiline": make_single_toggle_multiline,
        "multi_toggle": make_multi_toggle,
    }
    try:
        return factories[widget_cls]()
    except KeyError as exc:
        raise ValueError(f"Unknown widget class {widget_cls}") from exc


def _make_multi_select(
    parent: Qw.QWidget,
    schema: dict[str, ty.Any],
    func: OptionalCallback = None,
    *,
    n_max: int,
) -> Qw.QWidget:
    """Build a ``QtMultiSelect`` lazily to avoid importing heavier modules eagerly."""
    from qtextra.widgets.qt_select_multi import QtMultiSelect

    kwargs: dict[str, ty.Any] = {"func_changed": func, "sort": True, **schema}
    if n_max:
        kwargs["n_max"] = n_max
    return QtMultiSelect.from_schema(parent, **kwargs)


def _make_toggle_group(
    parent: Qw.QWidget,
    schema: dict[str, ty.Any],
    func: OptionalCallback = None,
    **kwargs: ty.Any,
) -> Qw.QWidget:
    """Build a ``QtToggleGroup`` lazily."""
    from qtextra.widgets.qt_toggle_group import QtToggleGroup

    return QtToggleGroup.from_schema(parent, func=func, **kwargs, **schema)


def _wrap_widget_with_metadata(
    parent: Qw.QWidget,
    widget: Qw.QWidget,
    schema: dict[str, ty.Any],
) -> Qw.QHBoxLayout | None:
    """Wrap a widget with help, info, or warning affordances when requested."""
    layout: Qw.QHBoxLayout | None = None

    for key, factory in (
        ("warning", qp.make_warning_label),
        ("help", qp.make_help_label),
        ("info", qp.make_info_label),
    ):
        message = schema.get(key)
        if not message:
            continue
        label_widget = factory(parent, message, normal=True)
        if layout is None:
            layout = qp.make_h_layout(label_widget, widget, spacing=1, stretch_id=(1,))
        else:
            layout.insertWidget(0, label_widget)
    return layout


def get_widget_for_schema(
    parent: Qw.QWidget,
    schema: dict[str, ty.Any],
    func: OptionalCallback = None,
) -> tuple[
    Qw.QLabel | Qw.QLineEdit | Qw.QCheckBox | Qw.QSpinBox | Qw.QDoubleSpinBox | Qw.QComboBox | QtMultiSelect,
    QtToggleGroup | Qw.QHBoxLayout | None,
]:
    """Build a widget and optional surrounding layout from a schema definition."""
    widget_cls = _resolve_widget_cls(schema)
    widget = _make_widget(parent, widget_cls, schema, func=func)

    if schema.get("regex") and hasattr(widget, "setValidator"):
        qp.set_regex_validator(widget, schema["regex"])

    if not schema.get("show", True):
        widget.hide()

    layout = _wrap_widget_with_metadata(parent, widget, schema)
    return widget, layout  # type: ignore[return-value]


def get_value_from_widget(widget: Qw.QWidget) -> ty.Any:
    """Extract a Python value from a supported widget."""
    from qtextra.widgets.qt_combobox_check import QtCheckableComboBox
    from qtextra.widgets.qt_select_multi import QtMultiSelect
    from qtextra.widgets.qt_toggle_group import QtToggleGroup

    if isinstance(widget, Qw.QLineEdit):
        return widget.text()
    if isinstance(widget, Qw.QCheckBox):
        return widget.isChecked()
    if isinstance(widget, (Qw.QDoubleSpinBox, Qw.QSpinBox)):
        return widget.value()
    if isinstance(widget, Qw.QComboBox):
        return widget.currentText()
    if isinstance(widget, Qw.QLabel):
        return widget.text()
    if isinstance(widget, QtCheckableComboBox):
        return widget.checked_texts()
    if isinstance(widget, QtMultiSelect):
        checked = widget.get_checked()
        if widget.n_max == 1:
            return checked[0] if checked else None
        return checked
    if isinstance(widget, QtToggleGroup):
        return widget.value
    raise ValueError(f"Unknown widget class {widget}")


def set_value_to_widget(widget: Qw.QWidget, value: ty.Any) -> None:
    """Apply a Python value to a supported widget."""
    from qtextra.widgets.qt_combobox_check import QtCheckableComboBox
    from qtextra.widgets.qt_select_multi import QtMultiSelect
    from qtextra.widgets.qt_toggle_group import QtToggleGroup

    if isinstance(widget, Qw.QLineEdit):
        if isinstance(value, list):
            value = ",".join(str(v) for v in value)
        elif value is None:
            value = ""
        widget.setText(str(value))
        return
    if isinstance(widget, Qw.QLabel):
        widget.setText("" if value is None else str(value))
        return
    if isinstance(widget, Qw.QCheckBox):
        widget.setChecked(bool(value))
        return
    if isinstance(widget, (Qw.QDoubleSpinBox, Qw.QSpinBox)):
        widget.setValue(value)
        return
    if isinstance(widget, QtCheckableComboBox):
        value = value or []
        widget.set_checked_texts([str(v) for v in value])
        return
    if isinstance(widget, Qw.QComboBox):
        if str(value) == "" and widget.itemText(0) == "None":
            value = widget.itemText(0)
        widget.setCurrentText("" if value is None else str(value))
        return
    if isinstance(widget, QtMultiSelect):
        widget.set_selected_options(value)
        return
    if isinstance(widget, QtToggleGroup):
        widget.value = value
        return
    raise ValueError(f"Unknown widget class {widget}")


def get_data_for_widgets(widgets: dict[str, Qw.QWidget], **kwargs: ty.Any) -> dict[str, ty.Any]:
    """Collect values from widgets into a plain dictionary."""
    data = {}
    for key, widget in widgets.items():
        if key.startswith("_"):
            continue
        data[key] = get_value_from_widget(widget)
    data.update(kwargs)
    return data
