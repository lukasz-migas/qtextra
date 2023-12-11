"""Various helpers to make making of UI elements easier."""
from __future__ import annotations

import os.path
import typing as ty
from contextlib import contextmanager
from enum import Enum
from functools import partial
from pathlib import Path

import numpy as np
import qtawesome as qta
import qtpy.QtWidgets as Qw
from koyo.typing import PathLike
from qtpy.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt, QTimer
from qtpy.QtGui import QColor, QCursor, QFont, QGuiApplication, QIcon, QImage, QMovie, QPixmap
from superqt import QElidingLabel, QLabeledSlider

from qtextra.utils.utilities import IS_MAC, IS_WIN

if ty.TYPE_CHECKING:
    from qtextra.widgets.qt_action import QtQtaAction
    from qtextra.widgets.qt_buttons import QtActivePushButton, QtPushButton, QtRichTextButton
    from qtextra.widgets.qt_click_label import QtClickableLabel
    from qtextra.widgets.qt_collapsible import QtCheckCollapsible
    from qtextra.widgets.qt_color_button import QtColorSwatch
    from qtextra.widgets.qt_eliding_label import QtElidingLabel
    from qtextra.widgets.qt_icon_label import QtIconLabel, QtQtaLabel
    from qtextra.widgets.qt_image_button import QtImagePushButton, QtLockButton, QtToolbarPushButton
    from qtextra.widgets.qt_line import QtHorzLine, QtVertLine
    from qtextra.widgets.qt_multi_select import QtMultiSelect
    from qtextra.widgets.qt_overlay import QtOverlayDismissMessage
    from qtextra.widgets.qt_progress_bar import QtLabeledProgressBar
    from qtextra.widgets.qt_progress_button import QtActiveProgressBarButton
    from qtextra.widgets.qt_scroll_label import QtScrollableLabel
    from qtextra.widgets.qt_searchable_combobox import QtSearchableComboBox
    from qtextra.widgets.qt_tool_button import QtToolButton

    try:
        from napari.utils.events.custom_types import Array
    except ImportError:
        Array = None


def make_form_layout(
    widget: ty.Optional[Qw.QWidget] = None, *widgets: ty.Tuple, stretch_after: bool = False
) -> Qw.QFormLayout:
    """Make form layout."""
    layout = Qw.QFormLayout(widget)
    layout.setFieldGrowthPolicy(Qw.QFormLayout.ExpandingFieldsGrow)
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    layout.setRowWrapPolicy(Qw.QFormLayout.DontWrapRows)
    for widget_ in widgets:
        layout.addRow(*widget_)
    if stretch_after:
        layout.addRow(make_spacer_widget())
    return layout


def find_row_for_widget(layout: Qw.QFormLayout, widget: Qw.QWidget):
    """Find row for widget in form layout."""
    row = None
    for row in range(layout.rowCount()):
        item = layout.itemAt(row, Qw.QFormLayout.ItemRole.FieldRole)
        if item == widget:
            break
        if item and item.widget() == widget:
            break
        item = layout.itemAt(row, Qw.QFormLayout.ItemRole.LabelRole)
        if item and item.widget() == widget:
            break
    return row


def find_row_for_label_in_form_layout(layout: Qw.QFormLayout, label: str) -> ty.Optional[int]:
    """Find index at which label is located in form layout."""
    row = None
    for row in range(layout.rowCount()):
        item = layout.itemAt(row, Qw.QFormLayout.ItemRole.LabelRole)
        if item and item.widget().text() == label:
            break
    return row


def remove_widget_in_form_layout(layout: Qw.QFormLayout, label: str):
    """Replace widget in form layout."""
    row = find_row_for_label_in_form_layout(layout, label)
    if row is not None:
        label = layout.itemAt(row, Qw.QFormLayout.LabelRole)  # type: ignore
        label_widget = label.widget()
        field = layout.itemAt(row, Qw.QFormLayout.FieldRole)  # type: ignore
        field_widget = field.widget()
        layout.removeItem(label)
        layout.removeItem(field)
        layout.removeRow(row)
        return row, label_widget, field_widget
    return None, None, None


def insert_widget_in_form_layout(
    layout: Qw.QFormLayout, row: int, label: Qw.QWidget, widget_or_layout: ty.Union[Qw.QWidget, Qw.QLayout]
):
    """Insert widget in form layout."""
    layout.insertRow(row, label, widget_or_layout)


def make_hbox_layout(
    widget: Qw.QWidget = None, spacing: int = 0, content_margins: ty.Optional[ty.Tuple[int, int, int, int]] = None
):
    """Make horizontal box layout."""
    layout = Qw.QHBoxLayout(widget)
    layout.setSpacing(spacing)
    if content_margins:
        layout.setContentsMargins(*content_margins)
    return layout


def make_vbox_layout(widget: Qw.QWidget = None, spacing: int = 0):
    """Make vertical box layout."""
    layout = Qw.QVBoxLayout(widget)
    layout.setSpacing(spacing)
    return layout


def set_layout_margin(layout: Qw.QLayout, margin: int):
    """Set layout margin."""
    if hasattr(layout, "setMargin"):
        layout.setMargin(margin)


def set_from_schema(widget: Qw.QWidget, schema: ty.Dict[str, ty.Any], **kwargs):
    """Set certain values on the model."""
    with qt_signals_blocked(widget):
        if "description" in schema:
            widget.setToolTip(schema["description"])


def call_later(parent: Qw.QWidget, func: ty.Callable, delay: int) -> None:
    """Call later."""
    QTimer(parent).singleShot(int(delay), func)


run_delayed = call_later


def make_periodic_timer(parent: Qw.QWidget, func: ty.Callable, delay: int, start: bool = True) -> QTimer:
    """Create periodic timer."""
    timer = QTimer(parent)
    timer.timeout.connect(func)
    timer.setInterval(delay)
    if start:
        timer.start()
    return timer


def combobox_setter(
    widget: Qw.QComboBox,
    clear: bool = True,
    items: ty.Optional[ty.Iterable[str]] = None,
    find_item: ty.Optional[str] = None,
    set_item: ty.Optional[str] = None,
):
    """Combobox setter that blocks any signals."""
    with qt_signals_blocked(widget):
        if clear:
            widget.clear()
        if items:
            widget.addItems(items)
        if find_item:
            v = widget.findText(find_item)
            if v == -1:
                widget.insertItem(0, find_item)
        if set_item:
            widget.setCurrentText(set_item)


def get_combobox_data_name_map(combobox: Qw.QComboBox):
    """Return mapping of data to name for combobox."""
    return {combobox.itemData(index): combobox.itemText(index) for index in range(combobox.count())}


def check_if_combobox_needs_update(combobox: Qw.QComboBox, new_data: ty.Dict[ty.Any, str]):
    """Check whether model data is equivalent to new data."""
    existing_data = get_combobox_data_name_map(combobox)
    return new_data != existing_data


def increment_combobox(
    combobox: Qw.QComboBox,
    direction: int,
    reset_func: ty.Optional[ty.Callable] = None,
    skip: list[int] | None = None,
    skipped: bool = False,
):
    """Increment combobox."""
    idx = combobox.currentIndex()
    count = combobox.count()
    idx += direction
    if direction == 0 and callable(reset_func):
        reset_func.emit()
    if idx >= count:
        idx = 0
    if idx < 0:
        idx = count - 1
    if skip is not None and idx in skip and not skipped:
        with qt_signals_blocked(combobox):
            combobox.setCurrentIndex(idx)
        increment_combobox(combobox, direction, reset_func, skip, skipped=len(skip) > count)
    else:
        combobox.setCurrentIndex(idx)


def make_label(
    parent: Qw.QWidget | None,
    text: str = "",
    enable_url: bool = False,
    alignment=None,
    wrap: bool = False,
    object_name: str = "",
    bold: bool = False,
    font_size: ty.Optional[int] = None,
    tooltip: ty.Optional[str] = None,
    selectable: bool = False,
    visible: bool = True,
) -> Qw.QLabel:
    """Make QLabel element."""
    widget = Qw.QLabel(parent)
    widget.setText(text)
    widget.setObjectName(object_name)
    if enable_url:
        widget.setTextFormat(Qt.RichText)  # type: ignore[attr-defined]
        widget.setTextInteractionFlags(widget.textInteractionFlags() | Qt.TextBrowserInteraction)
        widget.setOpenExternalLinks(True)
    if alignment is not None:
        widget.setAlignment(alignment)
    if bold:
        set_bold(widget, bold)
    if tooltip:
        widget.setToolTip(tooltip)
    if font_size:
        set_font(widget, font_size=font_size, bold=bold)
    if selectable:
        widget.setTextInteractionFlags(widget.textInteractionFlags() | Qt.TextSelectableByMouse)
    widget.setWordWrap(wrap)
    widget.setVisible(visible)
    return widget


def make_scrollable_label(
    parent: Qw.QWidget | None,
    text: str = "",
    enable_url: bool = False,
    alignment=None,
    wrap: bool = False,
    object_name: str = "",
    bold: bool = False,
    font_size: ty.Optional[int] = None,
    tooltip: ty.Optional[str] = None,
    selectable: bool = False,
    visible: bool = True,
) -> QtScrollableLabel:
    """Make QLabel element."""
    from qtextra.widgets.qt_scroll_label import QtScrollableLabel

    widget = QtScrollableLabel(parent, text=text)
    widget.setObjectName(object_name)
    widget.label.setObjectName(object_name)
    if enable_url:
        widget.label.setTextFormat(Qt.RichText)
        widget.label.setTextInteractionFlags(widget.label.textInteractionFlags() | Qt.TextBrowserInteraction)
        widget.label.setOpenExternalLinks(True)
    if alignment is not None:
        widget.label.setAlignment(alignment)
    if bold:
        set_bold(widget.label, bold)
    if tooltip:
        widget.setToolTip(tooltip)
    if font_size:
        set_font(widget.label, font_size=font_size, bold=bold)
    if selectable:
        widget.label.setTextInteractionFlags(widget.label.textInteractionFlags() | Qt.TextSelectableByMouse)
    widget.label.setWordWrap(wrap)
    widget.setVisible(visible)
    return widget


def make_click_label(
    parent: Qw.QWidget | None,
    text: str = "",
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    bold: bool = False,
    elide: Qt.TextElideMode = Qt.ElideNone,
    tooltip: str = "",
) -> QtClickableLabel:
    """Make clickable label."""
    from qtextra.widgets.qt_click_label import QtClickableLabel

    widget = QtClickableLabel(text, parent)
    widget.setElideMode(elide)
    if bold:
        set_bold(widget, bold)
    if tooltip:
        widget.setToolTip(tooltip)
    if func:
        [widget.evt_clicked.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_qta_label(
    parent: Qw.QWidget | None,
    icon_name: str,
    alignment=None,
    tooltip: ty.Optional[str] = None,
    xsmall: bool = False,
    small: bool = False,
    normal: bool = False,
    average: bool = False,
    medium: bool = False,
    large: bool = False,
    retain_size: bool = False,
    **kwargs,
) -> QtQtaLabel:
    """Make QLabel element."""
    from qtextra.widgets.qt_icon_label import QtQtaLabel

    widget = QtQtaLabel(parent=parent)
    widget.set_qta(icon_name, **kwargs)
    if xsmall:
        widget.set_xsmall()
    if small:
        widget.set_small()
    elif normal:
        widget.set_normal()
    elif average:
        widget.set_average()
    elif medium:
        widget.set_medium()
    elif large:
        widget.set_large()
    if alignment is not None:
        widget.setAlignment(alignment)
    if tooltip:
        widget.setToolTip(tooltip)
    if retain_size:
        set_retain_hidden_size_policy(widget)
    return widget


def set_tooltip(widget: Qw.QWidget, tooltip: str):
    """Set tooltip on specified widget."""
    widget.setToolTip(tooltip)


def make_eliding_label(
    parent: Qw.QWidget | None,
    text: str,
    enable_url: bool = False,
    alignment=None,
    wrap: bool = False,
    object_name: str = "",
    bold: bool = False,
    tooltip: ty.Optional[str] = None,
    elide: Qt.TextElideMode = Qt.ElideMiddle,
    font_size: ty.Optional[int] = None,
) -> QtElidingLabel:
    """Make single-line QLabel with automatic eliding."""
    from qtextra.widgets.qt_eliding_label import QtElidingLabel

    widget = QtElidingLabel(parent=parent, elide=elide)
    widget.setElideMode(elide)
    widget.setText(text)
    widget.setObjectName(object_name)
    if enable_url:
        widget.setTextFormat(Qt.RichText)
        widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
        widget.setOpenExternalLinks(True)
    if alignment is not None:
        widget.setAlignment(alignment)
    if font_size:
        set_font(widget, font_size=font_size, bold=bold)
    if bold:
        set_bold(widget, bold)
    if tooltip:
        widget.setToolTip(tooltip)
    widget.setWordWrap(wrap)
    return widget


def make_eliding_label2(
    parent: Qw.QWidget | None,
    text: str = "",
    enable_url: bool = False,
    alignment=None,
    wrap: bool = False,
    object_name: str = "",
    bold: bool = False,
    tooltip: ty.Optional[str] = None,
    elide: Qt.TextElideMode = Qt.ElideMiddle,
    font_size: ty.Optional[int] = None,
) -> QElidingLabel:
    """Make single-line QLabel with automatic eliding."""
    widget = QElidingLabel(parent=parent)  # , elide=elide)
    widget.setElideMode(elide)
    widget.setText(text)
    widget.setObjectName(object_name)
    if enable_url:
        widget.setTextFormat(Qt.RichText)
        widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
        widget.setOpenExternalLinks(True)
    if alignment is not None:
        widget.setAlignment(alignment)
    if font_size:
        set_font(widget, font_size=font_size, bold=bold)
    if bold:
        set_bold(widget, bold)
    if tooltip:
        widget.setToolTip(tooltip)
    widget.setWordWrap(wrap)
    return widget


def make_line_edit(
    parent: Qw.QWidget | None,
    text: str = "",
    tooltip: ty.Optional[str] = None,
    placeholder: str = "",
    bold: bool = False,
    font_size: ty.Optional[int] = None,
    object_name: str = "",
    validator=None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    func_changed: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    default: str = "",
    disabled: bool = False,
    **_kwargs,
) -> Qw.QLineEdit:
    """Make QLineEdit."""
    if default:
        text = default
    widget = Qw.QLineEdit(parent)
    widget.setText(text)
    widget.setClearButtonEnabled(True)
    if font_size:
        set_font(widget, font_size=font_size, bold=bold)
    if bold:
        set_bold(widget, bold)
    if tooltip:
        widget.setToolTip(tooltip)
    if object_name:
        widget.setObjectName(object_name)
    if validator:
        widget.setValidator(validator)
    if func:
        [widget.editingFinished.connect(func_) for func_ in _validate_func(func)]
    if func_changed:
        [widget.textChanged.connect(func_) for func_ in _validate_func(func_changed)]
    widget.setDisabled(disabled)
    widget.setPlaceholderText(placeholder)
    return widget


def make_text_edit(
    parent: Qw.QWidget | None, text: str = "", tooltip: ty.Optional[str] = None, placeholder: str = ""
) -> Qw.QTextEdit:
    """Make QTextEdit - a multiline version of QLineEdit."""
    widget = Qw.QTextEdit(parent)
    widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    widget.setPlaceholderText(placeholder)
    return widget


def make_multi_select(
    parent: Qw.QWidget,
    description: str = "",
    options: list[str] | None = None,
    value: str = "",
    default: str = "",
    placeholder: str = "Select...",
    func: ty.Callable | ty.Sequence[ty.Callable] | None = None,
    func_changed: ty.Callable | ty.Sequence[ty.Callable] | None = None,
    items: dict[str, ty.Any] | None = None,
    show_btn: bool = True,
    **kwargs: ty.Any,
) -> QtMultiSelect:
    """Make multi select."""
    from qtextra.widgets.qt_multi_select import QtMultiSelect

    return QtMultiSelect.from_schema(
        parent,
        description=description,
        options=options,
        value=value,
        default=default,
        placeholder=placeholder,
        func=func,
        func_changed=func_changed,
        items=items,
        show_btn=show_btn,
        **kwargs,
    )


def make_combobox(
    parent: Qw.QWidget | None,
    items: ty.Optional[ty.Iterable[str]] = None,
    tooltip: ty.Optional[str] = None,
    enum: ty.Optional[ty.List[str]] = None,
    options: ty.Optional[ty.List[str]] = None,
    value: ty.Optional[str] = None,
    default: ty.Optional[str] = None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    expand: bool = True,
    object_name: ty.Optional[str] = None,
    data: dict | None = None,
    **kwargs: ty.Any,
) -> Qw.QComboBox:
    """Make QComboBox."""
    if enum is not None:
        items = enum
    if value is None:
        value = default
    if options is not None:
        items = options
    widget = Qw.QComboBox(parent)
    if items:
        widget.addItems(items)
    if object_name:
        widget.setObjectName(object_name)
    if value and not data:
        widget.setCurrentText(value)
    tooltip = kwargs.get("description", tooltip)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    if data:
        set_combobox_data(widget, data, value)
    if func:
        [widget.currentTextChanged.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_checkable_combobox(
    parent: Qw.QWidget | None,
    items: ty.Optional[ty.Iterable[str]] = None,
    tooltip: ty.Optional[str] = None,
    enum: ty.Optional[ty.List[str]] = None,
    options: ty.Optional[ty.List[str]] = None,
    value: ty.Optional[str] = None,
    default: ty.Optional[str] = None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    expand: bool = True,
    data: dict | None = None,
    **kwargs: ty.Any,
) -> Qw.QComboBox:
    """Make QComboBox."""
    from qtextra.widgets.qt_checkable_combobox import QtCheckableComboBox

    if enum is not None:
        items = enum
    if options is not None:
        items = options
    if value is None:
        value = default
    widget = QtCheckableComboBox(parent)
    if items:
        widget.addItems(items)
    if value and not data:
        widget.setCurrentText(value)
    tooltip = kwargs.get("description", tooltip)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    if data:
        set_combobox_data(widget, data, value)
    if func:
        [widget.currentTextChanged.connect(func_) for func_ in _validate_func(func)]
        [widget.evt_checked.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_colormap_combobox(
    parent: Qw.QWidget | None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    default: str = "magma",
    label_min_width: int = 0,
):
    """Make colormap combobox."""
    from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
    from napari.utils.colormaps import AVAILABLE_COLORMAPS

    def _update_colormap(value):
        colormap = AVAILABLE_COLORMAPS[value]
        cbar = colormap.colorbar
        # Note that QImage expects the image width followed by height
        image = QImage(
            cbar,
            cbar.shape[1],
            cbar.shape[0],
            QImage.Format_RGBA8888,
        )
        widget_label.setPixmap(QPixmap.fromImage(image))

    widget_label = make_label(parent, "", object_name="colorbar")
    widget_label.setScaledContents(True)
    if label_min_width:
        widget_label.setMinimumWidth(label_min_width)
    widget = QtColormapComboBox(parent)
    widget.currentTextChanged.connect(_update_colormap)
    widget.setObjectName("colormapComboBox")
    widget.addItems(AVAILABLE_COLORMAPS)
    widget._allitems = set(AVAILABLE_COLORMAPS)
    widget.setCurrentText(default)
    if func:
        [widget.currentTextChanged.connect(func_) for func_ in _validate_func(func)]
    return widget, make_h_layout(widget_label, widget, stretch_id=[1], spacing=0)


def make_colormap_combobox_alone(
    parent: Qw.QWidget = None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    default: str = "magma",
):
    """Make colormap combobox."""
    from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
    from napari.utils.colormaps import AVAILABLE_COLORMAPS

    widget = QtColormapComboBox(parent)
    widget.setObjectName("colormapComboBox")
    widget.addItems(AVAILABLE_COLORMAPS)
    widget._allitems = set(AVAILABLE_COLORMAPS)
    widget.setCurrentText(default)
    if func:
        [widget.currentTextChanged.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_searchable_combobox(
    parent: Qw.QWidget | None,
    items: ty.Optional[ty.Iterable[str]] = None,
    tooltip: ty.Optional[str] = None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    enum: ty.Optional[ty.List[str]] = None,
    options: ty.Optional[ty.List[str]] = None,
    value: ty.Optional[str] = None,
    default: ty.Optional[str] = None,
    expand: bool = True,
    object_name: ty.Optional[str] = None,
    data=None,
    **kwargs,
) -> QtSearchableComboBox:
    """Make QComboBox."""
    from qtextra.widgets.qt_searchable_combobox import QtSearchableComboBox

    if enum is not None:
        items = enum
    if options is not None:
        items = options
    if value is None:
        value = default
    widget = QtSearchableComboBox(parent)
    if items:
        widget.addItems(items)
    if object_name:
        widget.setObjectName(object_name)
    if value and not data:
        widget.setCurrentText(value)
    tooltip = kwargs.get("description", tooltip)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    if data:
        set_combobox_data(widget, data, value)
    if func:
        [widget.currentTextChanged.connect(func_) for func_ in _validate_func(func)]
    return widget


def set_combobox_data(
    widget: Qw.QComboBox, data: ty.Union[ty.Dict, ty.OrderedDict, Enum], current_item: ty.Optional[str] = None
):
    """Set data/value on combobox."""
    if not isinstance(data, (ty.Dict, ty.OrderedDict)):
        data = {m: m.value for m in data}

    for index, (item, text) in enumerate(data.items()):
        if not isinstance(text, str):
            text = item.value
        widget.addItem(text, item)

        if current_item is not None:
            if current_item == item or current_item == text:
                widget.setCurrentIndex(index)


def set_combobox_text_data(
    widget: Qw.QComboBox, data: ty.Union[ty.List[str], ty.Dict[str, ty.Any]], current_item: ty.Optional[str] = None
):
    """Set data/value on combobox."""
    if isinstance(data, ty.List):
        data = {m: m for m in data}
    for index, (text, item) in enumerate(data.items()):
        widget.addItem(text, item)
        if current_item is not None:
            if current_item == item or current_item == text:
                widget.setCurrentIndex(index)


def set_combobox_current_index(widget: Qw.QComboBox, current_data):
    """Set current index on combobox."""
    for index in range(widget.count()):
        if widget.itemData(index) == current_data:
            widget.setCurrentIndex(index)
            break


def make_icon(path: str) -> QIcon:
    """Make an icon."""
    icon = QIcon()
    icon.addPixmap(QPixmap(path), QIcon.Normal, QIcon.Off)
    return icon


def make_qta_icon(name: str, color: ty.Optional[str] = None, **kwargs):
    """Make QTA label."""
    from qtextra.assets import get_icon
    from qtextra.config import THEMES

    name = get_icon(name)
    if color is None:
        color = THEMES.get_hex_color("icon")
    icon = qta.icon(name, color=color, **kwargs)
    return icon


def make_svg_label(parent: Qw.QWidget | None, object_name: str, tooltip: ty.Optional[str] = None) -> QtIconLabel:
    """Make icon label."""
    widget = QtIconLabel(parent=parent, object_name=object_name)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def make_btn(
    parent: Qw.QWidget | None,
    text: str,
    tooltip: ty.Optional[str] = None,
    flat: bool = False,
    checkable=False,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    font_size: ty.Optional[int] = None,
    bold: bool = False,
    object_name: str = "",
) -> QtPushButton:
    """Make button."""
    from qtextra.widgets.qt_buttons import QtPushButton

    widget = QtPushButton(parent=parent)
    widget.setText(text)
    widget.setCheckable(checkable)
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    if font_size:
        set_font(widget, font_size=font_size)
    if bold:
        set_bold(widget, bold)
    if func:
        [widget.clicked.connect(func_) for func_ in _validate_func(func)]
    if object_name:
        widget.setObjectName(object_name)
    return widget


def make_tool_btn(
    parent: Qw.QWidget | None,
    text: str,
    tooltip: ty.Optional[str] = None,
    flat: bool = False,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    font_size: ty.Optional[int] = None,
) -> QtPushButton:
    """Make button."""
    from qtextra.widgets.qt_tool_button import QtToolButton

    widget = QtToolButton(parent=parent)
    widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    if font_size:
        set_font(widget, font_size=font_size)
    if func:
        [widget.clicked.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_rich_btn(
    parent: Qw.QWidget | None, text: str, tooltip: ty.Optional[str] = None, flat: bool = False
) -> QtRichTextButton:
    """Make button."""
    from qtextra.widgets.qt_buttons import QtRichTextButton

    widget = QtRichTextButton(parent, text)
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    return widget


def make_active_btn(
    parent: Qw.QWidget | None,
    text: str,
    tooltip: ty.Optional[str] = None,
    flat: bool = False,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
) -> QtActivePushButton:
    """Make button with activity indicator."""
    from qtextra.widgets.qt_buttons import QtActivePushButton

    widget = QtActivePushButton(parent=parent)
    widget.setParent(parent)
    widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    if func:
        [widget.clicked.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_active_progress_btn(
    parent: Qw.QWidget | None,
    text: str,
    tooltip: ty.Optional[str] = None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    cancel_func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
) -> QtActiveProgressBarButton:
    """Make button with activity indicator."""
    from qtextra.widgets.qt_progress_button import QtActiveProgressBarButton

    widget = QtActiveProgressBarButton(parent=parent)
    widget.setParent(parent)
    widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    if func:
        [widget.evt_clicked.connect(func_) for func_ in _validate_func(func)]
    if cancel_func:
        [widget.evt_cancel.connect(func_) for func_ in _validate_func(cancel_func)]
    return widget


def make_scroll_area(
    parent: Qw.QWidget | None,
    vertical=Qt.ScrollBarPolicy.ScrollBarAsNeeded,
    horizontal=Qt.ScrollBarPolicy.ScrollBarAsNeeded,
):
    """Make scroll area."""
    scroll_area = Qw.QWidget(parent)
    scroll_widget = Qw.QScrollArea(parent)
    scroll_widget.setWidget(scroll_area)
    scroll_widget.setWidgetResizable(True)
    scroll_widget.setVerticalScrollBarPolicy(vertical)
    scroll_widget.setHorizontalScrollBarPolicy(horizontal)
    scroll_widget.setSizePolicy(Qw.QSizePolicy.Expanding, Qw.QSizePolicy.Expanding)  # type: ignore[attr-defined]
    return scroll_area, scroll_widget


def make_qta_btn(
    parent: Qw.QWidget | None,
    icon_name: str,
    tooltip: ty.Optional[str] = None,
    flat: bool = False,
    checkable: bool = False,
    small: bool = False,
    normal: bool = False,
    average: bool = False,
    medium: bool = False,
    large: bool = False,
    size: ty.Optional[ty.Tuple[int, int]] = None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    object_name: str = "",
    retain_size: bool = False,
    checked: bool = False,
    func_menu: ty.Optional[ty.Callable] = None,
    checked_icon_name: str = "",
    properties: ty.Optional[dict[str, ty.Any]] = None,
    label: str = "",
    standout: bool = False,
    **kwargs,
) -> QtImagePushButton:
    """Make button with qtawesome icon."""
    from qtextra.widgets.qt_image_button import QtImagePushButton

    widget = QtImagePushButton(parent=parent)
    widget.set_qta(icon_name, **kwargs)
    widget.set_default_size(small=small, normal=normal, average=average, medium=medium, large=large)
    if size and len(size) == 2:
        widget.set_size(size)
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    if checkable:
        widget.setCheckable(checkable)
        widget.setChecked(checked)
    if checked_icon_name:
        widget.set_toggle_qta(icon_name, checked_icon_name, **kwargs)
    if object_name:
        widget.setObjectName(object_name)
    if func:
        [widget.clicked.connect(func_) for func_ in _validate_func(func)]
    if func_menu:
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(func_menu)
    if retain_size:
        set_retain_hidden_size_policy(widget)
    if properties:
        for key, value in properties.items():
            widget.setProperty(key, value)
        polish_widget(widget)
    if label:
        widget.setText(label)
        widget.setProperty("with_text", True)
    if standout:
        widget.setProperty("standout", True)
    return widget


def make_lock_btn(
    parent: Qw.QWidget | None,
    small: bool = False,
    normal: bool = False,
    medium: bool = False,
    large: bool = False,
    size: ty.Optional[ty.Tuple[int, int]] = None,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    tooltip: ty.Optional[str] = None,
) -> QtLockButton:
    """Make lock button."""
    from qtextra.widgets.qt_image_button import QtLockButton

    widget = QtLockButton(parent=parent)
    widget.auto_connect()
    if func:
        [widget.clicked.connect(func_) for func_ in _validate_func(func)]
    if small:
        widget.set_small()
    elif normal:
        widget.set_normal()
    elif medium:
        widget.set_medium()
    elif large:
        widget.set_large()
    if size and len(size) == 2:
        widget.set_size(size)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def make_svg_btn(
    parent: Qw.QWidget | None,
    object_name: str,
    text: str = "",
    tooltip: ty.Optional[str] = None,
    flat: bool = False,
    checkable: bool = False,
) -> QtImagePushButton:
    """Make button."""
    from qtextra.widgets.qt_image_button import QtImagePushButton

    widget = QtImagePushButton(parent=parent)
    widget.setObjectName(object_name)
    widget.setText(text)
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    if checkable:
        widget.setCheckable(checkable)
    return widget


def make_toolbar_btn(
    parent: Qw.QWidget | None,
    name: str,
    text: str = "",
    tooltip: ty.Optional[str] = None,
    flat: bool = False,
    checkable: bool = False,
    medium: bool = False,
    large: bool = False,
    icon_kwargs=None,
) -> QtToolbarPushButton:
    """Make button."""
    from qtextra.widgets.qt_image_button import QtToolbarPushButton

    if icon_kwargs is None:
        icon_kwargs = {}

    widget = QtToolbarPushButton(parent=parent)
    widget.set_qta(name, **icon_kwargs)
    widget.setText(text)
    if medium:
        widget.set_medium()
    if large:
        widget.set_large()
    if tooltip:
        widget.setToolTip(tooltip)
    if flat:
        widget.setFlat(flat)
    if checkable:
        widget.setCheckable(checkable)
    return widget


def make_swatch(
    parent: Qw.QWidget | None,
    default: ty.Union[str, np.ndarray],
    tooltip: str = "",
    value: ty.Optional[ty.Union[str, np.ndarray]] = None,
    **kwargs,
) -> QtColorSwatch:
    """Make color swatch."""
    from qtextra.widgets.qt_color_button import QtColorSwatch

    if value is None:
        value = default
    tooltip = kwargs.get("description", tooltip)
    widget = QtColorSwatch(parent, initial_color=value, tooltip=tooltip)
    return widget


def make_swatch_grid(parent: Qw.QWidget | None, colors: ty.Iterable[str], func: ty.Callable):
    """Make grid of swatches."""
    from koyo.utilities import chunks

    _i = 0
    layout, swatches = Qw.QVBoxLayout(), []
    for _colors in chunks(colors, 10):
        row_layout = Qw.QHBoxLayout()
        row_layout.addSpacerItem(make_h_spacer())
        for _i, color in enumerate(_colors):
            swatch = make_swatch(parent, color, value=color)
            swatch.setMinimumSize(32, 32)
            swatch.evt_color_changed.connect(partial(func, _i))
            row_layout.addWidget(swatch)
            swatches.append(swatch)
            _i += 1
        row_layout.addSpacerItem(make_h_spacer())
        layout.addLayout(row_layout)
    return layout, swatches


def set_menu_on_bitmap_btn(widget: Qw.QPushButton, menu: Qw.QMenu):
    """Set menu on bitmap button."""
    widget.setMenu(menu)
    if IS_MAC:
        widget.setMinimumSize(QSize(55, 32))
    else:
        widget.setStyleSheet("QPushButton::menu-indicator { image: none; width : 0px; left:}")


def make_bitmap_tool_btn(
    parent: Qw.QWidget | None,
    icon: QIcon,
    min_size: ty.Optional[ty.Tuple[int]] = None,
    max_size: ty.Optional[ty.Tuple[int]] = None,
    tooltip: ty.Optional[str] = None,
) -> QtToolButton:
    """Make bitmap button."""
    from qtextra.widgets.qt_tool_button import QtToolButton

    widget = QtToolButton(parent)
    widget.setIcon(icon)
    if min_size is not None:
        widget.setMinimumSize(QSize(*min_size))
    if max_size is not None:
        widget.setMaximumSize(QSize(*max_size))
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def _validate_func(func: ty.Union[ty.Callable, ty.Sequence[ty.Callable]]) -> ty.Sequence[ty.Callable]:
    if callable(func):
        func = [func]
    return [func for func in func if callable(func)]


def make_checkbox(
    parent: Qw.QWidget | None,
    text: str = "",
    tooltip: ty.Optional[str] = None,
    default: bool = False,
    value: ty.Optional[bool] = None,
    expand: bool = True,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    clicked: ty.Optional[ty.Callable] = None,
    tristate: bool = False,
    model: ty.Optional[ty.Callable] = None,
    **kwargs,
) -> Qw.QCheckBox:
    """Make checkbox."""
    if value is None:
        value = default
    tooltip = kwargs.get("description", tooltip)
    widget = (model or Qw.QCheckBox)(parent)
    widget.setText(text)
    widget.setChecked(value)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    if tristate:
        widget.setTristate(tristate)
    if func:
        [widget.stateChanged.connect(func_) for func_ in _validate_func(func)]
    if clicked:
        widget.clicked.connect(clicked)
    return widget


def make_slider(
    parent: Qw.QWidget | None,
    minimum: float = 0,
    maximum: float = 100,
    step_size: float = 1,
    orientation="horizontal",
    tooltip: ty.Optional[str] = None,
    default: float = 1,
    value: ty.Optional[float] = None,
    expand: bool = True,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    **kwargs,
) -> Qw.QSlider:
    """Make slider."""
    if value is None:
        value = default
    tooltip = kwargs.get("description", tooltip)
    orientation = Qt.Orientation.Horizontal if orientation.lower() else Qt.Orientation.Vertical
    widget = Qw.QSlider(parent=parent)
    widget.setRange(minimum, maximum)
    widget.setOrientation(orientation)
    widget.setPageStep(step_size)
    widget.setValue(value)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    return widget


def make_slider_with_text(
    parent: ty.Optional[Qw.QWidget],
    min_value: int = 0,
    max_value: int = 100,
    step_size: int = 1,
    value: int = 1,
    orientation="horizontal",
    tooltip: ty.Optional[str] = None,
    focus_policy: Qt.FocusPolicy = Qt.FocusPolicy.TabFocus,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
) -> Qw.QSlider:
    """Make QSlider."""
    from superqt import QLabeledSlider

    orientation = Qt.Orientation.Horizontal if orientation.lower() else Qt.Orientation.Vertical
    widget = QLabeledSlider(orientation, parent)
    widget.setRange(min_value, max_value)
    widget.setValue(value)
    widget.setPageStep(step_size)
    widget.setFocusPolicy(focus_policy)
    if tooltip:
        widget.setToolTip(tooltip)
    if func:
        [widget.valueChanged.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_double_slider_with_text(
    parent: ty.Optional[Qw.QWidget],
    min_value: float = 0,
    max_value: float = 100,
    step_size: float = 1,
    value: float = 1,
    n_decimals: int = 1,
    orientation="horizontal",
    tooltip: ty.Optional[str] = None,
    focus_policy: Qt.FocusPolicy = Qt.FocusPolicy.TabFocus,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
) -> Qw.QSlider:
    """Make QSlider."""
    from superqt import QLabeledDoubleSlider

    orientation = Qt.Orientation.Horizontal if orientation.lower() else Qt.Orientation.Vertical
    widget = QLabeledDoubleSlider(orientation, parent)
    widget.setRange(min_value, max_value)
    widget.setDecimals(n_decimals)
    widget.setValue(value)
    widget.setPageStep(step_size)
    widget.setFocusPolicy(focus_policy)
    if tooltip:
        widget.setToolTip(tooltip)
    if func:
        [widget.valueChanged.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_labelled_slider(
    parent: Qw.QWidget | None,
    minimum: float = 0,
    maximum: float = 100,
    step_size: float = 1,
    orientation="horizontal",
    tooltip: ty.Optional[str] = None,
    default: float = 1,
    value: ty.Optional[float] = None,
    expand: bool = True,
    **kwargs,
) -> QLabeledSlider:
    """Make QtLabelledSlider."""
    if value is None:
        value = default
    tooltip = kwargs.get("description", tooltip)
    orientation = Qt.Orientation.Horizontal if orientation.lower() else Qt.Orientation.Vertical
    widget = QLabeledSlider(parent=parent)
    widget.setRange(minimum, maximum)
    widget.setOrientation(orientation)
    widget.setPageStep(step_size)
    widget.setValue(value)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    return widget


def make_int_spin_box(
    parent: Qw.QWidget | None,
    minimum: int = 0,
    maximum: int = 100,
    step_size: int = 1,
    default: int = 1,
    tooltip: ty.Optional[str] = None,
    value: ty.Optional[int] = None,
    prefix: ty.Optional[str] = None,
    suffix: ty.Optional[str] = None,
    expand: bool = True,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    keyboard_tracking: ty.Optional[bool] = None,
    **kwargs,
) -> Qw.QSpinBox:
    """Make double spinbox."""
    if value is None:
        value = default
    tooltip = kwargs.get("description", tooltip)
    widget = Qw.QSpinBox(parent)
    widget.setMinimum(minimum)
    widget.setMaximum(maximum)
    widget.setValue(value)
    widget.setSingleStep(step_size)
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if keyboard_tracking is not None:
        widget.setKeyboardTracking(keyboard_tracking)
    if tooltip:
        widget.setToolTip(tooltip)
    if prefix:
        widget.setPrefix(prefix)
    if suffix:
        widget.setSuffix(suffix)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    if func:
        [widget.valueChanged.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_double_spin_box(
    parent: Qw.QWidget | None,
    minimum: float = 0,
    maximum: float = 100,
    step_size: float = 0.01,
    default: float = 1,
    n_decimals: int = 1,
    tooltip: ty.Optional[str] = None,
    value: ty.Optional[float] = None,
    prefix: ty.Optional[str] = None,
    suffix: ty.Optional[str] = None,
    expand: bool = True,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    **kwargs,
) -> Qw.QDoubleSpinBox:
    """Make double spinbox."""
    if value is None:
        value = default
    tooltip = kwargs.get("description", tooltip)
    widget = Qw.QDoubleSpinBox(parent)
    widget.setDecimals(n_decimals)
    widget.setMinimum(minimum)
    widget.setMaximum(maximum)
    widget.setValue(value)
    widget.setSingleStep(step_size)
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if prefix:
        widget.setPrefix(prefix)
    if suffix:
        widget.setSuffix(suffix)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    if func:
        [widget.valueChanged.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_radio_btn(
    parent: Qw.QWidget | None,
    title: str,
    tooltip: ty.Optional[str] = None,
    expand: bool = True,
    checked: bool = False,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    **_kwargs,
) -> Qw.QRadioButton:
    """Make radio button."""
    widget = Qw.QRadioButton(parent)
    widget.setText(title)
    if tooltip:
        widget.setToolTip(tooltip)
    if expand:
        widget.setSizePolicy(Qw.QSizePolicy.MinimumExpanding, Qw.QSizePolicy.Minimum)  # type: ignore[attr-defined]
    if checked:
        widget.setChecked(checked)
    if func:
        [widget.clicked.connect(func_) for func_ in _validate_func(func)]
    return widget


def make_radio_btn_group(parent: Qw.QWidget | None, radio_buttons) -> Qw.QButtonGroup:
    """Make radio button group."""
    widget = Qw.QButtonGroup(parent)
    for btn_id, radio_btn in enumerate(radio_buttons):
        widget.addButton(radio_btn, btn_id)
    return widget


def make_h_line_with_text(label: str, parent: Qw.QWidget = None, bold: bool = False):
    """Make horizontal line with text."""
    return make_h_layout(
        make_h_line(parent), make_label(parent, label, bold=bold), make_h_line(parent), stretch_id=(0, 2)
    )


def make_h_line(parent: Qw.QWidget = None, thin: bool = False) -> QtHorzLine:
    """Make horizontal line."""
    from qtextra.widgets.qt_line import QtHorzLine

    widget = QtHorzLine(parent)
    if thin:
        widget.setFrameShape(Qw.QFrame.HLine)
        widget.setFrameShadow(Qw.QFrame.Plain)
        widget.setObjectName("thin")
    return widget


def make_v_line(parent: Qw.QWidget = None, thin: bool = False) -> QtVertLine:
    """Make horizontal line."""
    from qtextra.widgets.qt_line import QtVertLine

    widget = QtVertLine(parent)
    if thin:
        widget.setObjectName("thin")
    return widget


def make_v_spacer(x: int = 40, y: int = 20) -> Qw.QSpacerItem:
    """Make vertical QSpacerItem."""
    widget = Qw.QSpacerItem(x, y, Qw.QSizePolicy.Preferred, Qw.QSizePolicy.Expanding)  # type: ignore[attr-defined]
    return widget


def make_h_spacer(x: int = 40, y: int = 20) -> Qw.QSpacerItem:
    """Make horizontal QSpacerItem."""
    widget = Qw.QSpacerItem(x, y, Qw.QSizePolicy.Expanding, Qw.QSizePolicy.Preferred)  # type: ignore[attr-defined]
    return widget


def make_v_layout(
    *widgets: ty.Union[Qw.QWidget, Qw.QSpacerItem, Qw.QLayout],
    stretch_id: ty.Optional[ty.Union[int, ty.Sequence[int]]] = None,
    spacing: ty.Optional[int] = None,
    margin: ty.Optional[int] = None,
    alignment: ty.Optional[str] = None,
    stretch_before: bool = False,
    stretch_after: bool = False,
) -> Qw.QVBoxLayout:
    """Make vertical layout."""
    layout = Qw.QVBoxLayout()
    if spacing is not None:
        layout.setSpacing(spacing)
    return _set_in_layout(
        *widgets,
        layout=layout,
        stretch_id=stretch_id,
        alignment=alignment,
        stretch_before=stretch_before,
        stretch_after=stretch_after,
    )


def make_h_layout(
    *widgets: ty.Union[Qw.QWidget, Qw.QSpacerItem, Qw.QLayout],
    stretch_id: ty.Optional[ty.Union[int, ty.Sequence[int]]] = None,
    spacing: ty.Optional[int] = None,
    margin: ty.Optional[int] = None,
    alignment: ty.Optional[str] = None,
    stretch_before: bool = False,
    stretch_after: bool = False,
) -> Qw.QLayout:
    """Make horizontal layout."""
    layout = Qw.QHBoxLayout()
    if spacing is not None:
        layout.setSpacing(spacing)
    return _set_in_layout(
        *widgets,
        layout=layout,
        stretch_id=stretch_id,
        alignment=alignment,
        stretch_before=stretch_before,
        stretch_after=stretch_after,
    )


def _set_in_layout(
    *widgets,
    layout: Qw.QLayout,
    stretch_id: int,
    alignment: ty.Optional[str] = None,
    stretch_before: bool = False,
    stretch_after: bool = False,
):
    if stretch_before:
        layout.addStretch(True)
    for widget in widgets:
        if isinstance(widget, Qw.QLayout):
            layout.addLayout(widget)
        elif isinstance(widget, Qw.QSpacerItem):
            layout.addSpacerItem(widget)
        else:
            layout.addWidget(widget)
    if stretch_id is not None:
        if isinstance(stretch_id, int):
            stretch_id = (stretch_id,)
        for st_id in stretch_id:
            layout.setStretch(st_id, True)
    if alignment:
        layout.setAlignment(alignment)
    if stretch_after:
        layout.addStretch(True)
    return layout


def make_progressbar(
    parent: Qw.QWidget | None, minimum: int = 0, maximum: int = 100, with_progress: bool = False
) -> ty.Union[Qw.QProgressBar, QtLabeledProgressBar]:
    """Make progressbar."""
    if with_progress:
        from qtextra.widgets.qt_progress_bar import QtLabeledProgressBar

        widget = QtLabeledProgressBar(parent)
    else:
        widget = Qw.QProgressBar(parent)
    widget.setMinimum(minimum)
    widget.setMaximum(maximum)
    return widget


def set_font(widget: Qw.QWidget, font_size: int = 7, font_weight: int = 50, bold: bool = False):
    """Set font on a widget."""
    font = QFont()
    font.setPointSize(font_size if IS_WIN else font_size + 2)
    font.setWeight(QFont.Weight(font_weight))
    font.setBold(bold)
    widget.setFont(font)


def set_bold(widget: Qw.QWidget, bold: bool = True) -> Qw.QWidget:
    """Set text on widget as bold."""
    font = widget.font()
    font.setBold(bold)
    widget.setFont(font)
    return widget


def update_widget_style(widget: Qw.QWidget, object_name: str):
    """Update widget style by forcing its re-polish."""
    widget.setObjectName(object_name)
    widget.style().polish(widget)


def update_property(widget: Qw.QWidget, prop: str, value: ty.Any) -> None:
    """Update properties of widget to update style."""
    widget.setProperty(prop, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def polish_widget(*widget: Qw.QWidget):
    """Update widget style."""
    for widget_ in widget:
        widget_.style().unpolish(widget_)
        widget_.style().polish(widget_)


def make_advanced_collapsible(parent: Qw.QWidget, title: str = "Advanced options") -> QtCheckCollapsible:
    """Make collapsible widget."""
    content = Qw.QWidget()
    content.setLayout(make_form_layout())
    advanced_widget = QtCheckCollapsible(title, parent)
    advanced_widget.setContent(content)
    advanced_widget.collapse(False)
    return advanced_widget


def get_font(font_size: int, font_weight: int = QFont.Normal) -> QFont:
    """Get font."""
    font = QFont(QFont().defaultFamily(), weight=font_weight)
    font.setPointSize(font_size if IS_WIN else font_size + 2)
    return font


def set_sizer_policy(
    widget: Qw.QWidget,
    min_size: ty.Union[QSize, ty.Tuple[int]] = None,
    max_size: ty.Union[QSize, ty.Tuple[int]] = None,
    h_stretch: bool = False,
    v_stretch: bool = False,
):
    """Set sizer policy."""
    size_policy = Qw.QSizePolicy(Qw.QSizePolicy.Policy.Minimum, Qw.QSizePolicy.Policy.Preferred)
    size_policy.setHorizontalStretch(h_stretch)
    size_policy.setVerticalStretch(v_stretch)
    size_policy.setHeightForWidth(widget.sizePolicy().hasHeightForWidth())
    widget.setSizePolicy(size_policy)
    if min_size:
        widget.setMinimumSize(QSize(min_size))
    if max_size:
        widget.setMaximumSize(QSize(max_size))


def set_expanding_sizer_policy(
    widget: Qw.QWidget,
    horz: bool = False,
    vert: bool = False,
    expanding: Qw.QSizePolicy.Policy = Qw.QSizePolicy.Policy.MinimumExpanding,
    not_expanding: Qw.QSizePolicy.Policy = Qw.QSizePolicy.Policy.Preferred,
    h_stretch: bool = False,
    v_stretch: bool = False,
):
    """Set expanding policy."""
    size_policy = Qw.QSizePolicy(not_expanding if not horz else expanding, not_expanding if not vert else expanding)
    widget.setSizePolicy(size_policy)
    size_policy.setHorizontalStretch(h_stretch)
    size_policy.setVerticalStretch(v_stretch)


def set_retain_hidden_size_policy(widget: Qw.QWidget) -> None:
    """Set hidden policy."""
    policy = widget.sizePolicy()
    policy.setRetainSizeWhenHidden(True)
    widget.setSizePolicy(policy)


def make_group_box(parent: Qw.QWidget | None, title: str, is_flat: bool = True) -> Qw.QGroupBox:
    """Make group box."""
    widget = Qw.QGroupBox(parent)
    widget.setFlat(is_flat)
    widget.setTitle(title)
    return widget


def make_labelled_h_line(parent: Qw.QWidget | None, title: str) -> Qw.QHBoxLayout:
    """Make labelled line - similar to flat version of the group box."""
    layout = Qw.QHBoxLayout()
    layout.addWidget(make_label(parent, title), alignment=Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(make_h_line(parent), stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
    return layout


def make_menu(parent: Qw.QWidget | None, title: str = "") -> Qw.QMenu:
    """Make menu."""
    widget = Qw.QMenu(parent)
    widget.setTitle(title)
    return widget


def make_menu_item(
    parent: Qw.QWidget | None,
    title: str,
    shortcut: ty.Optional[str] = None,
    icon: ty.Union[QPixmap, str] = None,
    menu: Qw.QMenu = None,
    status_tip: ty.Optional[str] = None,
    tooltip: ty.Optional[str] = None,
    checkable: bool = False,
    func: ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]] = None,
    disabled: bool = False,
) -> QtQtaAction:
    """Make menu item."""
    from qtextra.widgets.qt_action import QtQtaAction

    widget = QtQtaAction(parent=parent)
    widget.setText(title)
    if shortcut is not None:
        widget.setShortcut(shortcut)
    if icon is not None:
        if isinstance(icon, str):
            widget.set_qta(icon)
        else:
            widget.setIcon(icon)
    if tooltip:
        widget.setToolTip(tooltip)
    if status_tip:
        widget.setStatusTip(status_tip)
    if checkable:
        widget.setCheckable(checkable)
    if menu is not None:
        menu.addAction(widget)
    if func:
        [widget.triggered.connect(func_) for func_ in _validate_func(func)]
    if disabled:
        widget.setDisabled(disabled)
    return widget


def make_menu_group(parent: Qw.QWidget, *actions):
    """Make actions group."""
    group = Qw.QActionGroup(parent)
    for action in actions:
        group.addAction(action)
    return group


def make_overlay_message(
    parent: Qw.QWidget | None,
    widget: Qw.QWidget,
    text: str = "",
    icon_name: str = "info",
    wrap: bool = True,
    dismiss_btn: bool = True,
    can_dismiss: bool = True,
    ok_btn: bool = False,
    ok_func=None,
    ok_text="OK",
) -> QtOverlayDismissMessage:
    """Add overlay message to widget."""
    from qtextra.widgets.qt_overlay import QtOverlayDismissMessage

    _widget = QtOverlayDismissMessage(
        parent,
        text,
        icon_name,
        word_wrap=wrap,
        dismiss_btn=dismiss_btn,
        can_dismiss=can_dismiss,
        ok_btn=ok_btn,
        ok_func=ok_func,
        ok_text=ok_text,
    )
    _widget.set_widget(widget)
    return _widget


def warn(parent: Qw.QWidget | None, message: str, title: str = "Warning"):
    """Create a pop up dialog with a warning message."""
    from qtpy.QtWidgets import QMessageBox

    dlg = QMessageBox(parent=parent, icon=QMessageBox.Warning)
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.exec_()


def toast(
    parent: Qw.QWidget | None,
    title: str,
    message: str,
    func: ty.Optional[ty.Callable] = None,
    position: ty.Literal["top_right", "top_left", "bottom_right", "bottom_left"] = "top_right",
    icon: ty.Literal["none", "debug", "info", "success", "warning", "error", "critical"] = "none",
):
    """Show notification."""
    from qtextra.widgets.qt_toast import QtToast

    if callable(func):
        func(message)
    QtToast(parent).show_message(title, message, position=position, icon=icon)


def long_toast(
    parent: Qw.QWidget | None,
    title: str,
    message: str,
    duration: int = 10000,
    func: ty.Optional[ty.Callable] = None,
    position: ty.Literal["top_right", "top_left", "bottom_right", "bottom_left"] = "top_right",
    icon: ty.Literal["none", "debug", "info", "success", "warning", "error", "critical"] = "none",
):
    """Show notification."""
    from qtextra.widgets.qt_toast import QtToast

    if callable(func):
        func(message)
    QtToast(parent).show_long_message(title, message, duration, position=position, icon=icon)


def hyper(link: Path | str, value: str | Path | None = None, prefix: str = "goto") -> str:
    """Parse into a hyperlink."""
    if value is None:
        value = link
    if isinstance(link, Path):
        return f"<a href='{link.as_uri()}'>{value}</a>"
    return f"<a href='{prefix}:{link}'>{value}</a>"


def open_filename(
    parent: Qw.QWidget | None, title: str = "Select file...", base_dir: str = "", file_filter: str = "*"
) -> str:
    """Get filename."""
    from qtpy.QtWidgets import QFileDialog

    filename, _ = QFileDialog.getOpenFileName(parent, title, base_dir, file_filter)
    return filename


def get_directory(
    parent: Qw.QWidget | None,
    title: str = "Select directory...",
    base_dir: ty.Optional[PathLike] = "",
    native: bool = True,
) -> ty.Optional[str]:
    """Get filename."""
    from qtpy.QtWidgets import QFileDialog

    options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
    if not native:
        options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks | QFileDialog.DontUseNativeDialog
    if base_dir is None:
        base_dir = ""

    return QFileDialog.getExistingDirectory(parent, title, str(base_dir), options=options)


def get_filename(
    parent: Qw.QWidget | None,
    title: str = "Save file...",
    base_dir: ty.Optional[PathLike] = "",
    file_filter: str = "*",
    base_filename: ty.Optional[str] = None,
    multiple: bool = False,
) -> str:
    """Get filename."""
    from qtpy.QtWidgets import QFileDialog

    if base_filename:
        base_dir = os.path.join(base_dir, base_filename)
    if multiple:
        filename, _ = QFileDialog.getOpenFileNames(
            parent,
            title,
            str(base_dir) or "",
            file_filter,
        )
    else:
        filename, _ = QFileDialog.getOpenFileName(
            parent,
            title,
            str(base_dir) or "",
            file_filter,
        )
    return filename


def get_save_filename(
    parent: Qw.QWidget | None,
    title: str = "Save file...",
    base_dir: ty.Optional[PathLike] = "",
    file_filter: str = "*",
    base_filename: ty.Optional[str] = None,
) -> str:
    """Get filename."""
    from qtpy.QtWidgets import QFileDialog

    if base_filename:
        base_dir = os.path.join(base_dir, base_filename)
    filename, _ = QFileDialog.getSaveFileName(parent, title, str(base_dir) or "", file_filter)
    return filename


def get_filename_with_path(
    parent: Qw.QWidget | None,
    path: str,
    filename: str,
    message: str = "Please specify filename that should be used to save the data.",
    title: str = "Save file...",
    extension: str = "",
) -> ty.Optional[str]:
    """Get filename by asking for the filename but also combining it with path."""
    from pathlib import Path

    filename = get_text(value=filename, parent=parent, label=message, title=title)
    if filename:
        return str((Path(path) / filename).with_suffix(extension))


def get_color(
    parent: Qw.QWidget | None, color: ty.Optional[np.ndarray] = None, as_hex: bool = True, as_array: bool = False
) -> np.ndarray:
    """Get color."""
    from qtpy.QtGui import QColor

    if as_array:
        as_hex = False
    if isinstance(color, str):
        color = QColor(color)
    elif isinstance(color, np.ndarray):
        color = QColor(*color.astype(int))

    # settings = get_settings()
    dlg = Qw.QColorDialog(color)
    # for i, _color in enumerate(settings.visuals.color_scheme):
    #     dlg.setCustomColor(i, QColor(_color))
    new_color: ty.Optional[ty.Union[str, np.ndarray]] = None
    if dlg.exec_():
        new_color = dlg.currentColor()
        if as_hex:
            new_color = new_color.name()
        if as_array:
            new_color = np.asarray(new_color.toTuple()) / 255
    return new_color


def confirm(parent: ty.Optional[Qw.QWidget], message: str, title: str = "Are you sure?") -> bool:
    """Confirm action."""
    from qtpy.QtWidgets import QDialog

    dlg = QDialog(parent)
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)  # type: ignore[attr-defined]
    dlg.setObjectName("confirm_dialog")
    dlg.setMinimumSize(350, 200)
    dlg.setWindowTitle(title)
    layout = make_v_layout()
    layout.addWidget(make_label(dlg, message, enable_url=True, wrap=True), stretch=True)
    layout.addLayout(
        make_h_layout(
            make_btn(dlg, "Yes", func=dlg.accept),
            make_btn(dlg, "No", func=dlg.reject),
        )
    )
    dlg.setLayout(layout)
    return bool(dlg.exec_())


def confirm_with_text(
    parent: Qw.QWidget,
    message: str = "Please confirm action by typing <b>confirm</b> to continue.",
    request: str = "confirm",
    title: str = "Please confirm...",
) -> bool:
    """Confirm action."""
    from qtextra.widgets.qt_confirm import ConfirmWithTextDialog

    if request not in message:
        if "<b>confirm</b>" not in message:
            raise ValueError("Request string must be part of the message.")
        message = message.replace("<b>confirm</b>", f"<b>{request}</b>")
    dlg = ConfirmWithTextDialog(parent, title, message, request)
    return bool(dlg.exec_())


def get_text(parent: Qw.QWidget, label: str = "New value", title: str = "Text", value: str = "") -> ty.Optional[str]:
    """Get text."""
    text, ok = Qw.QInputDialog.getText(parent, title, label, text=value)
    if ok:
        return text
    return None


def get_integer(
    parent: Qw.QWidget | None, label: str = "New value", title: str = "Text", minimum: int = 0, maximum: int = 100
) -> ty.Optional[int]:
    """Get text."""
    value, ok = Qw.QInputDialog.getInt(parent, title, label, minValue=minimum, maxValue=maximum)
    if ok:
        return value
    return None


def get_double(
    parent: Qw.QWidget | None,
    label: str = "New value",
    title: str = "Text",
    minimum: float = 0,
    maximum: float = 100,
    n_decimals: int = 2,
    step: float = 0.01,
) -> ty.Optional[float]:
    """Get text."""
    value, ok = Qw.QInputDialog.getDouble(
        parent, title, label, minValue=minimum, maxValue=maximum, decimals=n_decimals, step=step
    )
    if ok:
        return value
    return None


@contextmanager
def qt_signals_blocked(*obj, block_signals: bool = True) -> None:
    """Context manager to temporarily block signals from `obj`."""
    if not block_signals:
        yield
    else:
        [_obj.blockSignals(True) for _obj in obj]
        yield
        [_obj.blockSignals(False) for _obj in obj]


@contextmanager
def event_hook_removed() -> None:
    """Context manager to temporarily remove the PyQt5 input hook."""
    from qtpy import QtCore

    if hasattr(QtCore, "pyqtRemoveInputHook"):
        QtCore.pyqtRemoveInputHook()
    try:
        yield
    finally:
        if hasattr(QtCore, "pyqtRestoreInputHook"):
            QtCore.pyqtRestoreInputHook()


def enable_with_opacity(
    obj, widget_list: ty.Union[ty.Iterable[str], ty.Iterable[Qw.QWidget]], enabled: bool, min_opacity: float = 0.5
):
    """Enable widgets."""
    disable_with_opacity(obj, widget_list, not enabled, min_opacity)


def disable_with_opacity(
    obj: Qw.QWidget,
    widget_list: ty.Union[ty.Iterable[str], ty.Iterable[Qw.QWidget]],
    disabled: bool,
    min_opacity: float = 0.5,
) -> None:
    """Set enabled state on a list of widgets. If disabled, decrease opacity."""
    for wdg in widget_list:
        if isinstance(wdg, str):
            widget = getattr(obj, wdg)
        else:
            widget = wdg
        widget.setEnabled(not disabled)
        op = Qw.QGraphicsOpacityEffect(obj)
        op.setOpacity(min_opacity if disabled else 1.0)
        widget.setGraphicsEffect(op)


def disable_widgets(*objs: Qw.QWidget, disabled: bool, min_opacity: float = 0.5) -> None:
    """Set enabled state on a list of widgets. If disabled, decrease opacity."""
    for wdg in objs:
        wdg.setEnabled(not disabled)
        op = None
        if disabled:
            op = Qw.QGraphicsOpacityEffect(wdg)
            op.setOpacity(min_opacity if disabled else 1.0)
        if wdg.graphicsEffect() is not None and disabled:
            wdg.graphicsEffect().setEnabled(False)
        wdg.setGraphicsEffect(op)


def hide_widgets(*objs: Qw.QWidget, hidden: bool) -> None:
    """Set enabled state on a list of widgets. If disabled, decrease opacity."""
    for wdg in objs:
        wdg.setVisible(not hidden)


def set_opacity(widget, disabled: bool, min_opacity: float = 0.5) -> None:
    """Set opacity on object."""
    op = Qw.QGraphicsOpacityEffect(widget)
    op.setOpacity(min_opacity if disabled else 1.0)
    widget.setEnabled(not disabled)
    widget.setGraphicsEffect(op)


def make_spacer_widget(
    horz: Qw.QSizePolicy.Policy = Qw.QSizePolicy.Policy.Preferred,
    vert: Qw.QSizePolicy.Policy = Qw.QSizePolicy.Policy.Expanding,
) -> Qw.QWidget:
    """Make widget that fills space."""
    spacer = Qw.QWidget()
    spacer.setObjectName("toolbarSpacer")
    spacer.setSizePolicy(horz, vert)
    return spacer


def add_flash_animation(
    widget: Qw.QWidget, duration: int = 300, color: Array = (0.5, 0.5, 0.5, 0.5), n_loop: int = 1
) -> None:
    """Add flash animation to widget to highlight certain action (e.g. taking a screenshot).

    Parameters
    ----------
    widget : QWidget
        Any Qt widget.
    duration : int
        Duration of the flash animation.
    color : Array
        Color of the flash animation. By default, we use light gray.
    n_loop : int
        Number of times the animation should flash.

    """
    from napari.utils.colormaps.standardize_color import transform_color

    color = transform_color(color)[0]
    color = (255 * color).astype("int")

    effect = Qw.QGraphicsColorizeEffect(widget)
    widget.setGraphicsEffect(effect)

    widget._flash_animation = QPropertyAnimation(effect, b"color")
    widget._flash_animation.setStartValue(QColor(0, 0, 0, 0))
    widget._flash_animation.setEndValue(QColor(0, 0, 0, 0))
    widget._flash_animation.setLoopCount(n_loop)

    # let's make sure to remove the animation from the widget because
    # if we don't, the widget will actually be black and white.
    widget._flash_animation.finished.connect(partial(remove_flash_animation, widget))

    widget._flash_animation.start()

    # now  set an actual time for the flashing and an intermediate color
    widget._flash_animation.setDuration(duration)
    widget._flash_animation.setKeyValueAt(0.5, QColor(*color))


def add_highlight_animation(widget: Qw.QWidget, n_flashes: int = 3, duration: float = 250):
    """Add multiple rounds of flashes to widget."""
    effect = Qw.QGraphicsColorizeEffect(widget)
    widget.setGraphicsEffect(effect)

    widget._flash_animation = QPropertyAnimation(effect, b"color")
    widget._flash_animation.setStartValue(QColor(0, 0, 0, 0))
    widget._flash_animation.setEndValue(QColor(0, 0, 0, 0))
    widget._flash_animation.setLoopCount(n_flashes)

    # let's make sure to remove the animation from the widget because
    # if we don't, the widget will actually be black and white.
    widget._flash_animation.finished.connect(partial(remove_flash_animation, widget))

    widget._flash_animation.start()

    # now  set an actual time for the flashing and an intermediate color
    widget._flash_animation.setDuration(duration)
    widget._flash_animation.setKeyValueAt(0.5, QColor(255, 255, 255, 255))


def remove_flash_animation(widget: Qw.QWidget):
    """Remove flash animation from widget.

    Parameters
    ----------
    widget : QWidget
        Any Qt widget.
    """
    widget.setGraphicsEffect(None)
    del widget._flash_animation


def expand_animation(stack: Qw.QStackedWidget, start_width: int, end_width: int, duration: int = 500):
    """Create expand animation."""
    animation = QPropertyAnimation(stack, b"maximumWidth")
    # animation = QPropertyAnimation(stack, b"minimumWidth")
    stack._animation = animation
    stack._animation.finished.connect(partial(remove_expand_animation, stack))
    animation.setDuration(duration)
    animation.setLoopCount(1)
    animation.setStartValue(start_width)
    animation.setEndValue(end_width)
    animation.setEasingCurve(QEasingCurve.InOutQuart)
    animation.start()


def remove_expand_animation(widget: Qw.QWidget):
    """Remove expand animation from widget.

    Parameters
    ----------
    widget : QWidget
        Any Qt widget.
    """
    widget.setGraphicsEffect(None)
    del widget._animation


def make_loading_gif(parent: Qw.QWidget, which: str = "square", size=(20, 20)) -> ty.Tuple[Qw.QLabel, QMovie]:
    """Make QMovie animation using GIF."""
    from qtextra.assets import LOADING_CIRCLE_GIF, LOADING_SQUARE_GIF

    assert which.lower() in ["square", "circle"], "Incorrect gif selected - please use either `circle` or `square`"
    path = str(LOADING_CIRCLE_GIF if which == "circle" else LOADING_SQUARE_GIF)
    label, movie = make_gif_label(parent, path, size=size)
    set_retain_hidden_size_policy(label)
    return label, movie


def make_gif_label(parent: Qw.QWidget, path: str, size=(20, 20), start: bool = True) -> ty.Tuple[Qw.QLabel, QMovie]:
    """Make QMovie animation and place it in the label."""
    label = Qw.QLabel("Loading...", parent=parent)
    label.setScaledContents(True)
    movie = QMovie(path)
    if size is not None:
        label.setMaximumSize(*size)
        movie.setScaledSize(QSize(*size))
    label.setMovie(movie)
    if start:
        movie.start()
    return label, movie


def make_gif(which: str = "square", size=(20, 20), start: bool = True) -> QMovie:
    """Make movie."""
    from qtextra.assets import LOADING_CIRCLE_GIF, LOADING_SQUARE_GIF

    assert which.lower() in ["square", "circle"], "Incorrect gif selected - please use either `circle` or `square`"
    path = str(LOADING_CIRCLE_GIF if which == "circle" else LOADING_SQUARE_GIF)
    movie = QMovie(path)
    if size is not None:
        movie.setScaledSize(QSize(*size))
    if start:
        movie.start()
    return movie


def find_in_table(table: Qw.QTableWidget, column: int, text: str) -> ty.Optional[int]:
    """Find text in table."""
    for row in range(table.rowCount()):
        item = table.item(row, column)
        if item is not None and item.text() == text:
            return row
    return None


def make_progress_widget(
    widget,
    tooltip: str = "Click here to cancel the task.",
    with_progress: bool = False,
    with_cancel: bool = True,
    with_layout: bool = True,
):
    """Create progress widget and all other elements."""
    if with_cancel and not with_layout:
        raise ValueError("Cannot have cancel button without layout.")

    progress_widget = Qw.QWidget(widget)
    progress_widget.hide()
    progress_bar = make_progressbar(progress_widget, with_progress=with_progress)

    if with_layout:
        progress_layout = Qw.QHBoxLayout(progress_widget)
        progress_layout.addWidget(progress_bar, stretch=True, alignment=Qt.AlignmentFlag.AlignVCenter)
    else:
        progress_layout = None
    if with_cancel:
        cancel_btn = make_qta_btn(progress_widget, "cross_full", tooltip=tooltip)
        progress_layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
    else:
        cancel_btn = None
    return progress_layout, progress_widget, progress_bar, cancel_btn


def make_auto_update_layout(parent: Qw.QWidget, func: ty.Callable):
    """Make layout."""
    widget = make_btn(parent, "Update")
    if func:
        [widget.clicked.connect(func_) for func_ in _validate_func(func)]

    auto_update_check = make_checkbox(parent, "Auto-update")
    auto_update_check.stateChanged.connect(lambda check: disable_widgets(widget, disabled=check))
    auto_update_check.setChecked(True)

    layout = make_h_layout(widget, auto_update_check, stretch_id=(0,))
    return widget, auto_update_check, layout


def make_line_label(parent: Qw.QWidget | None, text: str, bold: bool = False) -> Qw.QHBoxLayout:
    """Make layout with `--- TEXT ---` which looks pretty nice."""
    return make_h_layout(
        make_h_line(parent), make_label(parent, text, bold=bold), make_h_line(parent), stretch_id=(0, 2)
    )


def parse_link_to_link_tag(link: str, desc_text: ty.Optional[str] = None) -> str:
    """Parse text link to change the color so it appears more reasonably in dark theme/."""
    from qtextra.config.theme import THEMES

    if desc_text is None:
        desc_text = link

    return f"""<a href="{link}" style="color: {THEMES.get_theme_color(key="text")}">{desc_text}</a>"""


def parse_path_to_link_tag(path: str, desc_text: ty.Optional[PathLike] = None) -> str:
    """Parse text link to change the color, so it appears more reasonably in dark theme."""
    import pathlib

    from qtextra.config.theme import THEMES

    if desc_text is None:
        desc_text = path

    path = str(pathlib.Path(path).as_uri())
    return f"""<a href="{path}" style="color: {THEMES.get_theme_color(key="text")}">{desc_text}</a>"""


def clear_layout(layout):
    """Clear layout."""
    if hasattr(layout, "count"):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                clear_layout(item.layout())


def collect_layout_widgets(layout: Qw.QLayout):
    """Remove widgets from layout without destroying them."""
    widgets = []

    def _collect_widgets(_layout):
        if hasattr(_layout, "count"):
            while _layout.count():
                item = _layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    _layout.removeWidget(widget)
                    widgets.append(widget)
                else:
                    _collect_widgets(item.layout())

    _collect_widgets(layout)
    return widgets


def parse_value_to_html(desc: str, value) -> str:
    """Parse value."""
    return f"<p><strong>{desc}</strong> {value}</p>"


def parse_title_message_to_html(title: str, message: str = ""):
    """Parse title and message to HTML.

    The final text will be formatted in such a way as the title is bold and the message is in standard font, separated
    by a new line.
    """
    return f"<strong>{title}</strong><p>{message}</p>"


def get_icon_from_img(path: PathLike) -> ty.Optional[QIcon]:
    """Get icon
    any type.

    Parameters
    ----------
    path: str
        relative or absolute path to the image file

    Returns
    -------
    icon : QIcon
        icon obtained
    """
    if not os.path.exists(path):
        return None

    icon = QIcon()
    icon.addPixmap(QPixmap(str(path)), QIcon.Normal, QIcon.Off)
    return icon


def disconnect_event(widget: Qw.QWidget, evt_name, func):
    """Safely disconnect event without raising RuntimeError."""
    try:
        getattr(widget, evt_name).disconnect(func)
    except RuntimeError:
        pass


def get_parent(parent):
    """Get top level parent."""
    if parent is None:
        app = Qw.QApplication.instance()
        if app:
            for i in app.topLevelWidgets():
                if isinstance(i, Qw.QMainWindow):  # pragma: no cover
                    parent = i
                    break
    return parent


def trim_dialog_size(dlg) -> ty.Tuple[int, int]:
    """Trim dialog size and retrieve new size."""
    win = get_parent(None)
    sh = dlg.sizeHint()
    cw, ch = sh.width(), sh.height()
    if win:
        win_size = win.size()
        mw, mh = win_size.width(), win_size.height()
        if cw > mw:
            cw = mw - 50
        if ch > mh:
            ch = mh - 50
    return cw, ch


def style_form_layout(layout: Qw.QFormLayout) -> None:
    """Override certain styles for macOS."""
    from qtextra.utils.utilities import IS_MAC

    if IS_MAC:
        layout.setVerticalSpacing(4)


def show_above_mouse(widget: Qw.QWidget, show: bool = True) -> None:
    """Show popup dialog above the mouse cursor position."""
    pos = QCursor().pos()  # mouse position
    sz_hint = widget.sizeHint()
    pos -= QPoint(sz_hint.width() / 2, sz_hint.height() + 14)  # type: ignore[call-overload]
    widget.move(pos)
    if show:
        widget.show()


def show_below_mouse(widget: Qw.QWidget, show: bool = True) -> None:
    """Show popup dialog below the mouse cursor position."""
    pos = QCursor().pos()  # mouse position
    sz_hint = widget.sizeHint()
    pos -= QPoint(sz_hint.width() / 2, -14)  # type: ignore[call-overload]
    widget.move(pos)
    if show:
        widget.show()


def show_left_of_mouse(widget: Qw.QWidget, show: bool = True) -> None:
    """Show popup dialog left of the mouse cursor position."""
    pos = QCursor().pos()  # mouse position
    sz_hint = widget.sizeHint()
    pos -= QPoint(sz_hint.width() + 14, sz_hint.height() / 4)  # type: ignore[call-overload]
    widget.move(pos)
    if show:
        widget.show()


def show_right_of_mouse(widget: Qw.QWidget, show: bool = True) -> None:
    """Show popup dialog left of the mouse cursor position."""
    pos = QCursor().pos()  # mouse position
    sz_hint = widget.sizeHint()
    pos -= QPoint(-14, sz_hint.height() / 4)  # type: ignore[call-overload]
    widget.move(pos)
    if show:
        widget.show()


def show_below_widget(
    widget: Qw.QWidget, parent: Qw.QWidget, show: bool = True, y_offset: int = 14, x_offset: int = 0
) -> None:
    """Show popup dialog above the widget."""
    rect = parent.rect()
    pos = parent.mapToGlobal(QPoint(rect.left() + rect.width() / 2, rect.top()))  # type: ignore[call-overload]
    sz_hint = widget.size()
    pos -= QPoint((sz_hint.width() / 2) - x_offset, -y_offset)  # type: ignore[call-overload]
    widget.move(pos)
    if show:
        widget.show()


def copy_text_to_clipboard(text: str) -> None:
    """Helper function to easily copy text to clipboard while notifying the user."""
    cb = QGuiApplication.clipboard()
    cb.setText(text)


def copy_image_to_clipboard(image: QImage) -> None:
    """Helper function to easily copy image to clipboard while notifying the user."""
    cb = QGuiApplication.clipboard()
    cb.setImage(image)
