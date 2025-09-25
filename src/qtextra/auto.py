"""Automatic UI generation."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QHBoxLayout, QLayout, QWidget

import qtextra.helpers as qp


def set_values_from_dict(
    data: dict[str, str | int | float | bool], widgets: dict[str, QWidget], block: bool = True
) -> None:
    """Set config to widgets."""
    for key, value in data.items():
        try:
            widget = widgets[key]
            with qp.qt_signals_blocked(widget, block_signals=block):
                qp.set_value_to_widget(widget, value)
        except KeyError:
            logger.error(f"Could not find widget for {key}")


def _append_widgets(
    widget: QWidget,
    layout: QFormLayout,
    widgets: tuple[QWidget, ...],
    label: str | None = None,
    search_widget: QWidget | None = None,
) -> tuple[QWidget, QFormLayout]:
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
    parent: QWidget,
    widget: QWidget,
    layout: QFormLayout,
    func: ty.Callable,
    label: str,
    icon: str = "help",
    tooltip: str = "Learn more...",
    extras: tuple[QWidget, ...] | None = None,
) -> tuple[QWidget, QFormLayout]:
    if extras is None:
        extras = ()
    return _add_widgets(
        widget,
        layout,
        label,
        widgets=(qp.make_qta_btn(parent, icon, average=True, func=func, tooltip=tooltip), *extras),
    )


def _add_widgets(
    widget: QWidget,
    layout: QFormLayout,
    label: str,
    widgets: tuple[QWidget, ...] = (),
    before_widgets: tuple[QWidget, ...] = (),
    spacing: int = 1,
) -> tuple[QWidget, QFormLayout]:
    """Add widgets to layout."""
    if widgets is None:
        widgets = ()
    if not before_widgets:
        before_widgets = ()
    if not widgets and not before_widgets:
        raise ValueError("No widgets provided")
    row, db_label, db_widget = qp.remove_widget_in_form_layout(layout, label)
    if row is not None:
        if isinstance(db_widget, QHBoxLayout):
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
    widget: QWidget,
    layout: QFormLayout,
    label: str,
    label_widget: QWidget | None,
    widget_widget: QWidget | QLayout,
) -> tuple[QWidget, QFormLayout]:
    row = qp.find_row_for_label_in_form_layout(layout, label)
    if row is not None:
        if label_widget is None:
            layout.insertRow(row, widget_widget)
        else:
            layout.insertRow(row, label_widget, widget_widget)
    return widget, layout


def _insert_after_widget(
    widget: QWidget,
    layout: QFormLayout,
    label: str,
    label_widget: QWidget | None,
    widget_widget: QWidget | QLayout,
) -> tuple[QWidget, QFormLayout]:
    row = qp.find_row_for_label_in_form_layout(layout, label)
    if row is not None:
        if label_widget is None:
            layout.insertRow(row + 1, widget_widget)
        else:
            layout.insertRow(row + 1, label_widget, widget_widget)
    return widget, layout
