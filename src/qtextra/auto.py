"""Automatic UI generation."""

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


def set_values_from_dict(
    data: dict[str, str | int | float | bool], widgets: dict[str, Qw.QWidget], block: bool = True
) -> None:
    """Set config to widgets."""
    for key, value in data.items():
        try:
            widget = widgets[key]
            with qp.qt_signals_blocked(widget, block_signals=block):
                set_value_to_widget(widget, value)
        except KeyError:
            logger.error(f"Could not find widget for {key}")


def _append_widgets(
    widget: Qw.QWidget,
    layout: Qw.QFormLayout,
    widgets: tuple[Qw.QWidget, ...],
    label: str | None = None,
    search_widget: Qw.QWidget | None = None,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    if widgets is None:
        raise ValueError("No widgets provided")
    new_layout = qp.make_h_layout(*widgets, spacing=1, alignment=Qt.AlignmentFlag.AlignVCenter)
    row = None
    if search_widget is not None:
        row = qp.find_row_for_widget(layout, search_widget)
        if row is not None:
            row += 1
    if label:
        if row is not None:
            layout.insertRow(row, qp.make_label(widget, label), new_layout)
        else:
            layout.addRow(qp.make_label(widget, label), new_layout)
    else:
        if row is not None:
            layout.insertRow(row, new_layout)
        else:
            layout.addRow(new_layout)
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
    widgets: tuple[Qw.QWidget, ...] = (),
    before_widgets: tuple[Qw.QWidget, ...] = (),
    spacing: int = 1,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    """Add widgets to layout."""
    if widgets is None:
        widgets = ()
    if not before_widgets:
        before_widgets = ()
    if not widgets and not before_widgets:
        raise ValueError("No widgets provided")
    row, db_label, db_widget = qp.remove_widget_in_form_layout(layout, label)
    if row is not None:
        if isinstance(db_widget, Qw.QHBoxLayout):
            new_layout = db_widget
            for wdg in widgets:
                new_layout.addWidget(wdg)
            for wdg in before_widgets:
                new_layout.insertWidget(0, wdg)
        else:
            new_layout = qp.make_h_layout(
                *before_widgets, db_widget, *widgets, stretch_id=len(before_widgets), spacing=spacing
            )
        qp.insert_widget_in_form_layout(layout, row, db_label, new_layout)
    return widget, layout


def _insert_before_widget(
    widget: Qw.QWidget,
    layout: Qw.QFormLayout,
    label: str,
    label_widget: Qw.QWidget | None,
    widget_widget: Qw.QWidget | Qw.QLayout,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
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
    widget_widget: Qw.QWidget | Qw.QLayout,
) -> tuple[Qw.QWidget, Qw.QFormLayout]:
    row = qp.find_row_for_label_in_form_layout(layout, label)
    if row is not None:
        if label_widget is None:
            layout.insertRow(row + 1, widget_widget)
        else:
            layout.insertRow(row + 1, label_widget, widget_widget)
    return widget, layout


def guess_widget_cls(schema: dict) -> str:
    """Guess widget class."""
    if "type" in schema:
        item_type = schema["type"]
    else:
        item_type = schema["anyOf"][0]["type"]
    if item_type in ["string", "array"]:
        if schema.get("enum"):
            return "combo_box"
        return "line_edit"
    elif item_type == "boolean":
        return "checkbox"
    elif item_type == "integer":
        return "int_spin_box"
    elif item_type == "number":
        return "double_spin_box"
    raise ValueError(f"Could not parse '{item_type}'")


def get_widget_for_schema(
    parent: Qw.QWidget, schema: dict, func: OptionalCallback = None
) -> tuple[
    Qw.QLabel | Qw.QLineEdit | Qw.QCheckBox | Qw.QSpinBox | Qw.QDoubleSpinBox | Qw.QComboBox | QtMultiSelect,
    QtToggleGroup | Qw.QHBoxLayout | None,
]:
    """Get widget for specified field."""
    from qtextra.widgets.qt_select_multi import QtMultiSelect
    from qtextra.widgets.qt_toggle_group import QtToggleGroup

    widget_cls = schema.get("widget_cls", None)
    if widget_cls is None:
        widget_cls = guess_widget_cls(schema)
    if isinstance(widget_cls, tuple):
        widget_cls, related_field = widget_cls

    layout: Qw.QLayout | None = None
    widget: (
        Qw.QLabel
        | Qw.QLineEdit
        | Qw.QCheckBox
        | Qw.QSpinBox
        | Qw.QDoubleSpinBox
        | Qw.QComboBox
        | QtMultiSelect
        | QtToggleGroup
    )
    if widget_cls == "line_edit":
        widget = qp.make_line_edit(parent, func=func, func_clear=func, **schema)
    elif widget_cls == "line_edit_changed":
        widget = qp.make_line_edit(parent, func_changed=func, func_clear=func, **schema)
    elif widget_cls == "disabled_line_edit":
        widget = qp.make_line_edit(parent, func=func, disabled=True, **schema)
    elif widget_cls == "disabled_line_edit_changed":
        widget = qp.make_line_edit(parent, func_changed=func, disabled=True, **schema)
    elif widget_cls == "disabled_label":
        widget = qp.make_label(parent, disabled=True, **schema)
    elif widget_cls == "checkbox":
        widget = qp.make_checkbox(parent, "", func=func, **schema)
    elif widget_cls == "checkbox_with_text":
        widget = qp.make_checkbox(parent, schema.get("title", ""), func=func, **schema)
    elif widget_cls == "int_spin_box":
        widget = qp.make_int_spin_box(parent, func=func, **schema)
    elif widget_cls == "double_spin_box":
        widget = qp.make_double_spin_box(parent, func=func, **schema)
    elif widget_cls == "combo_box":
        widget = qp.make_combobox(parent, func=func, **schema)
    elif widget_cls == "searchable_combo_box":
        widget = qp.make_searchable_combobox(parent, func_index=func, **schema)
    elif widget_cls == "multi_combo_box":
        widget = qp.make_checkable_combobox(parent, func=func, **schema)
    elif widget_cls == "multi_select":
        widget = QtMultiSelect.from_schema(parent, func_changed=func, sort=True, **schema)
    elif widget_cls == "single_select":
        widget = QtMultiSelect.from_schema(parent, func_changed=func, n_max=1, sort=True, **schema)
    elif widget_cls == "single_toggle":
        widget = QtToggleGroup.from_schema(parent, func=func, **schema)
    elif widget_cls == "single_toggle_multiline":
        widget = QtToggleGroup.from_schema(parent, func=func, multiline=True, **schema)
    elif widget_cls == "multi_toggle":
        widget = QtToggleGroup.from_schema(parent, func=func, exclusive=False, **schema)
    else:
        raise ValueError(f"Unknown widget class {widget_cls}")

    # add regex validator if needed
    if schema.get("regex") and hasattr(widget, "setValidator"):
        qp.set_regex_validator(widget, schema["regex"])

    # hide widget if needed
    if not schema.get("show", True):
        widget.hide()

    # check whether 'warning' is included with the widget, if so, add it into a layout
    if schema.get("warning"):
        warning_label = qp.make_warning_label(parent, schema["warning"], normal=True)
        layout = qp.make_h_layout(warning_label, widget, spacing=1, stretch_id=(1,))
    # check whether 'help' is included with the widget, if so, add it into a layout
    if schema.get("help"):
        help_label = qp.make_help_label(parent, schema["help"], normal=True)
        if layout is None:
            layout = qp.make_h_layout(help_label, widget, spacing=1, stretch_id=(1,))
        else:
            layout.insertWidget(0, help_label)  # type: ignore[attr-defined]
    # check whether 'info' is included with the widget, if so, add it into a layout
    if schema.get("info"):
        info_label = qp.make_info_label(parent, schema["info"], normal=True)
        if layout is None:
            layout = qp.make_h_layout(info_label, widget, spacing=1, stretch_id=(1,))
        else:
            layout.insertWidget(0, info_label)  # type: ignore[attr-defined]
    return widget, layout  # type: ignore[return-value]


def get_value_from_widget(widget: Qw.QWidget) -> ty.Any:
    """Get value from a widget."""
    from qtextra.widgets.qt_combobox_check import QtCheckableComboBox
    from qtextra.widgets.qt_select_multi import QtMultiSelect
    from qtextra.widgets.qt_toggle_group import QtToggleGroup

    if isinstance(widget, Qw.QLineEdit):
        return widget.text()
    elif isinstance(widget, Qw.QCheckBox):
        return widget.isChecked()
    elif isinstance(widget, (Qw.QDoubleSpinBox, Qw.QSpinBox)):
        return widget.value()
    elif isinstance(widget, Qw.QComboBox):
        return widget.currentText()
    elif isinstance(widget, Qw.QLabel):
        return widget.text()
    elif isinstance(widget, QtCheckableComboBox):
        return widget.checked_texts()
    elif isinstance(widget, QtMultiSelect):
        checked = widget.get_checked()
        if widget.n_max == 1:
            return checked[0] if checked else None
        return checked
    elif isinstance(widget, QtToggleGroup):
        return widget.value
    raise ValueError(f"Unknown widget class {widget}")


def set_value_to_widget(widget: Qw.QWidget, value: ty.Any) -> None:
    """Set value to widget."""
    from qtextra.widgets.qt_combobox_check import QtCheckableComboBox
    from qtextra.widgets.qt_select_multi import QtMultiSelect
    from qtextra.widgets.qt_toggle_group import QtToggleGroup

    if isinstance(widget, Qw.QLineEdit):
        if isinstance(value, list):
            value = ",".join([str(v) for v in value])
        elif value is None:
            value = ""
        widget.setText(str(value))
    elif isinstance(widget, Qw.QLabel):
        widget.setText(str(value))
    elif isinstance(widget, Qw.QCheckBox):
        widget.setChecked(value)
    elif isinstance(widget, (Qw.QDoubleSpinBox, Qw.QSpinBox)):
        widget.setValue(value)
    elif isinstance(widget, QtCheckableComboBox):
        value = value or []
        widget.set_checked_texts([str(v) for v in value])
    elif isinstance(widget, Qw.QComboBox):
        # if the value was incorrect, let's check if there 'None' which can be safely set
        if str(value) == "" and widget.itemText(0) == "None":
            value = widget.itemText(0)
        widget.setCurrentText(str(value))
    elif isinstance(widget, QtMultiSelect):
        widget.set_selected_options(value)
    elif isinstance(widget, QtToggleGroup):
        widget.value = value
    else:
        raise ValueError(f"Unknown widget class {widget}")


def get_data_for_widgets(widgets: dict[str, Qw.QWidget], **kwargs: ty.Any) -> dict[str, ty.Any]:
    """Get config for widgets."""
    data = {}
    for key, widget in widgets.items():
        if key.startswith("_"):
            continue
        data[key] = get_value_from_widget(widget)
    data.update(kwargs)
    return data
