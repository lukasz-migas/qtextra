"""Compact pill editor for typed key-value attributes."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QDoubleValidator, QIntValidator, QKeySequence, QMouseEvent, QShortcut
from qtpy.QtWidgets import QComboBox, QFrame, QLabel, QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dict_tag_editor import DictTagValue
from qtextra.widgets.qt_label_elide import QtElidingLabel
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayoutWidget


def _validate_value(value: DictTagValue) -> None:
    if value is not None and not isinstance(value, (str, int, float)):
        raise TypeError("Value must be str, int, float, or None.")


def _value_type(value: DictTagValue) -> str:
    if value is None:
        return "None"
    if isinstance(value, (bool, int)):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def _format_value(value: DictTagValue) -> str:
    return "None" if value is None else str(value)


class _QtAttributeEditorPopup(QFrame):
    """Small transient editor used for both new and existing attributes."""

    def __init__(
        self,
        parent: QWidget,
        commit: Callable[[str | None, str, DictTagValue], str | None],
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("attributeTagPopup")
        self._commit = commit
        self._original_key: str | None = None

        self.key_edit = hp.make_line_edit(self, placeholder="Key...", func_enter=self._save)
        self.value_edit = hp.make_line_edit(self, placeholder="Value...", func_enter=self._save)
        self.type_combo = QComboBox(self)
        self.type_combo.addItems(["str", "int", "float", "None"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        self.error_label = QLabel(self)
        self.error_label.setObjectName("attributeTagError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = hp.make_btn(self, "Add", func=self._save, object_name="save")
        self.cancel_button = hp.make_btn(self, "Cancel", func=self.hide, object_name="cancel")

        fields = hp.make_h_layout(self.key_edit, self.value_edit, self.type_combo, spacing=4, margin=0)
        fields.setStretch(0, 2)
        fields.setStretch(1, 2)
        actions = hp.make_h_layout(stretch_before=True, spacing=4, margin=0)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.save_button)
        hp.make_v_layout(fields, self.error_label, actions, spacing=6, margin=8, parent=self)

        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.activated.connect(self.hide)
        self._on_type_changed("str")

    def open_for(
        self,
        anchor: QWidget,
        key: str | None = None,
        value: DictTagValue = None,
    ) -> None:
        """Open the popup beneath an anchor for an add or edit operation."""
        self._original_key = key
        self._set_error("")
        self.key_edit.setText("" if key is None else key)
        self.type_combo.setCurrentText("str" if key is None else _value_type(value))
        self.value_edit.setText("" if key is None or value is None else str(value))
        self.adjustSize()
        hp.show_below_widget(self, anchor)
        self.raise_()
        self.activateWindow()
        self.key_edit.setFocus()
        self.key_edit.selectAll()

    def _save(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            self._set_error("Key cannot be empty.", self.key_edit)
            return

        try:
            value = self._coerce_value(self.value_edit.text(), self.type_combo.currentText())
        except ValueError as error:
            self._set_error(str(error), self.value_edit)
            return

        error = self._commit(self._original_key, key, value)
        if error:
            self._set_error(error, self.key_edit)
            return
        self.hide()

    def _set_error(self, message: str, invalid_widget: QWidget | None = None) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))
        self.key_edit.setProperty("invalid", False)
        self.value_edit.setProperty("invalid", False)
        if invalid_widget is not None:
            invalid_widget.setProperty("invalid", True)
        hp.polish_widget(self.key_edit)
        hp.polish_widget(self.value_edit)
        self.adjustSize()

    def _on_type_changed(self, value_type: str) -> None:
        if value_type == "int":
            self.value_edit.setValidator(QIntValidator(self))
            self.value_edit.setPlaceholderText("Integer value...")
            self.value_edit.setEnabled(True)
            return
        if value_type == "float":
            validator = QDoubleValidator(self)
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.value_edit.setValidator(validator)
            self.value_edit.setPlaceholderText("Float value...")
            self.value_edit.setEnabled(True)
            return

        self.value_edit.setValidator(None)
        if value_type == "None":
            self.value_edit.clear()
            self.value_edit.setPlaceholderText("No value")
            self.value_edit.setEnabled(False)
            return
        self.value_edit.setPlaceholderText("Value...")
        self.value_edit.setEnabled(True)

    @staticmethod
    def _coerce_value(text: str, value_type: str) -> DictTagValue:
        if value_type == "str":
            return text
        if value_type == "int":
            stripped = text.strip()
            if not stripped:
                raise ValueError("Integer value cannot be empty.")
            return int(stripped)
        if value_type == "float":
            stripped = text.strip()
            if not stripped:
                raise ValueError("Float value cannot be empty.")
            return float(stripped)
        if value_type == "None":
            return None
        raise ValueError(f"Unsupported value type: {value_type}")


class QtAttributeTagButton(QFrame):
    """Compact attribute pill with edit and delete actions."""

    evt_clicked = Signal(str)
    evt_delete_requested = Signal(str)

    def __init__(
        self,
        key: str,
        value: DictTagValue,
        parent: QWidget | None = None,
        *,
        maximum_width: int = 240,
    ) -> None:
        super().__init__(parent)
        self._key = key
        self._value = value
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMaximumHeight(28)
        if maximum_width > 0:
            self.setMaximumWidth(maximum_width)

        self.label = QtElidingLabel(parent=self, elide=Qt.TextElideMode.ElideMiddle)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setMinimumWidth(24)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.delete_button = hp.make_qta_btn(
            self,
            "cross",
            tooltip="Remove attribute.",
            flat=True,
            size_preset="xsmall",
            object_name="delete",
            func=self._request_delete,
        )
        self.delete_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = hp.make_h_layout(self.label, self.delete_button, spacing=2, margin=(7, 0, 1, 0), parent=self)
        layout.setStretch(0, 1)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_item(key, value)

    @property
    def key(self) -> str:
        """Return the attribute key."""
        return self._key

    @property
    def value(self) -> DictTagValue:
        """Return the typed attribute value."""
        return self._value

    @property
    def text(self) -> str:
        """Return the full text rendered by the pill."""
        return f"{self._key}: {_format_value(self._value)}"

    def set_item(self, key: str, value: DictTagValue) -> None:
        """Replace the key and value displayed by this pill."""
        self._key = key
        self._value = value
        self.label.setText(self.text)
        self.setToolTip(self.text)
        self.label.setToolTip(self.text)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Request editing when the pill body is clicked."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.evt_clicked.emit(self._key)
        super().mousePressEvent(event)

    def _request_delete(self) -> None:
        self.evt_delete_requested.emit(self._key)

    setItem = set_item


class QtAttributeTagManager(QWidget):
    """Manage compact pills representing a typed key-value dictionary."""

    evt_items_changed = Signal(dict)
    evt_item_added = Signal(str, object)
    evt_item_updated = Signal(str, str, object)
    evt_item_removed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        flow: bool = True,
        case_sensitive: bool = False,
        tag_maximum_width: int = 240,
    ) -> None:
        super().__init__(parent)
        self.case_sensitive = case_sensitive
        self.tag_maximum_width = tag_maximum_width
        self._items: dict[str, DictTagValue] = {}
        self.widgets: dict[str, QtAttributeTagButton] = {}

        self._tag_layout = (
            hp.make_flow_layout(horizontal_spacing=2, vertical_spacing=2, margin=0)
            if flow
            else QtScrollableHLayoutWidget(self)
        )
        if not flow:
            self._tag_layout.setSpacing(2)
            self._tag_layout.set_min_height(28)
            self._tag_layout.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = hp.make_h_layout(spacing=2, margin=0, parent=self)
        if flow:
            layout.addLayout(self._tag_layout, stretch=1)
        else:
            layout.addWidget(self._tag_layout, stretch=1)

        self.add_button = hp.make_qta_btn(
            self,
            "add",
            tooltip="Add attribute.",
            size_preset="average",
            standout=True,
            object_name="add",
            func=self._open_add_popup,
        )
        self.add_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.add_button, alignment=Qt.AlignmentFlag.AlignTop)

        self._popup = _QtAttributeEditorPopup(self, self._commit_popup)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def items(self) -> dict[str, DictTagValue]:
        """Return a copy of the attributes in display order."""
        return dict(self._items)

    def export_dict(self) -> dict[str, DictTagValue]:
        """Export the current attributes as a dictionary."""
        return self.items()

    def set_items(self, items: Mapping[str, DictTagValue]) -> None:
        """Replace all current attributes."""
        self.clear_items(emit_signal=False)
        for key, value in items.items():
            self._set_item(key, value, emit_signal=False)
        self._emit_items_changed()

    def add_item(self, key: str, value: DictTagValue) -> bool:
        """Add or update one attribute."""
        return self._set_item(key, value, emit_signal=True)

    def add_items(self, items: Mapping[str, DictTagValue]) -> list[str]:
        """Add or update several attributes and return the affected keys."""
        changed: list[str] = []
        for key, value in items.items():
            if self.add_item(key, value):
                changed.append(key.strip())
        return changed

    def remove_item(self, key: str) -> bool:
        """Remove an attribute by key."""
        existing_key = self._find_key(key)
        if existing_key is None:
            return False

        normalized = self._key_id(existing_key)
        widget = self.widgets.pop(normalized)
        self._items.pop(existing_key)
        self._remove_widget(widget)
        self.evt_item_removed.emit(existing_key)
        self._emit_items_changed()
        return True

    def clear_items(self, emit_signal: bool = True) -> None:
        """Remove every attribute."""
        for widget in list(self.widgets.values()):
            self._remove_widget(widget)
        self.widgets.clear()
        self._items.clear()
        if emit_signal:
            self._emit_items_changed()

    def has_item(self, key: str) -> bool:
        """Return whether an attribute key exists."""
        return self._find_key(key) is not None

    def get_value(self, key: str) -> DictTagValue:
        """Return the value associated with a key."""
        existing_key = self._find_key(key)
        if existing_key is None:
            raise KeyError(key)
        return self._items[existing_key]

    def edit_item(self, key: str) -> bool:
        """Open the popup editor for an existing attribute."""
        existing_key = self._find_key(key)
        if existing_key is None:
            return False
        widget = self.widgets[self._key_id(existing_key)]
        self._popup.open_for(widget, existing_key, self._items[existing_key])
        return True

    def _set_item(self, key: str, value: DictTagValue, *, emit_signal: bool) -> bool:
        _validate_value(value)
        display_key = key.strip()
        if not display_key:
            return False

        existing_key = self._find_key(display_key)
        if existing_key is None:
            self._items[display_key] = value
            widget = QtAttributeTagButton(
                display_key,
                value,
                self,
                maximum_width=self.tag_maximum_width,
            )
            widget.evt_clicked.connect(self.edit_item)
            widget.evt_delete_requested.connect(self.remove_item)
            self.widgets[self._key_id(display_key)] = widget
            self._tag_layout.addWidget(widget)
            if emit_signal:
                self.evt_item_added.emit(display_key, value)
                self._emit_items_changed()
            return True

        self._replace_item(existing_key, display_key, value)
        if emit_signal:
            self.evt_item_updated.emit(existing_key, display_key, value)
            self._emit_items_changed()
        return True

    def _replace_item(self, old_key: str, new_key: str, value: DictTagValue) -> None:
        normalized_old = self._key_id(old_key)
        widget = self.widgets.pop(normalized_old)
        updated: dict[str, DictTagValue] = {}
        for key, current_value in self._items.items():
            if key == old_key:
                updated[new_key] = value
            else:
                updated[key] = current_value
        self._items = updated
        widget.set_item(new_key, value)
        self.widgets[self._key_id(new_key)] = widget

    def _commit_popup(
        self,
        original_key: str | None,
        new_key: str,
        value: DictTagValue,
    ) -> str | None:
        existing_key = self._find_key(new_key)
        if original_key is None:
            if existing_key is not None:
                return "An attribute with this key already exists."
            self.add_item(new_key, value)
            return None

        source_key = self._find_key(original_key)
        if source_key is None:
            return "The attribute no longer exists."
        if existing_key is not None and existing_key != source_key:
            return "An attribute with this key already exists."

        self._replace_item(source_key, new_key, value)
        self.evt_item_updated.emit(source_key, new_key, value)
        self._emit_items_changed()
        return None

    def _open_add_popup(self) -> None:
        self._popup.open_for(self.add_button)

    def _find_key(self, key: str) -> str | None:
        normalized = self._key_id(key.strip())
        for existing_key in self._items:
            if self._key_id(existing_key) == normalized:
                return existing_key
        return None

    def _key_id(self, key: str) -> str:
        return key if self.case_sensitive else key.casefold()

    def _remove_widget(self, widget: QtAttributeTagButton) -> None:
        if isinstance(self._tag_layout, QtScrollableHLayoutWidget):
            self._tag_layout.removeWidget(widget)
            return
        for index in range(self._tag_layout.count()):
            if self._tag_layout.get_widget(index) is widget:
                self._tag_layout.removeWidgetOrLayout(index)
                return

    def _emit_items_changed(self) -> None:
        self.evt_items_changed.emit(self.export_dict())

    addItem = add_item
    addItems = add_items
    removeItem = remove_item
    clearItems = clear_items
    hasItem = has_item
    setItems = set_items
    getItems = items
    getValue = get_value
    editItem = edit_item
    exportDict = export_dict
