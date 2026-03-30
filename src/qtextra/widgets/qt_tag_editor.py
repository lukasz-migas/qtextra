"""Tag editor widget."""

from __future__ import annotations

import re

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import QLineEdit, QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_tag import QtTagButton
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayoutWidget


class _QtTagEditorLineEdit(QLineEdit):
    """Line edit that commits tags when token separators are typed."""

    evt_separator_pressed = Signal()

    def keyPressEvent(self, event: QKeyEvent | None) -> None:  # type: ignore[override]
        if event and event.key() in {Qt.Key.Key_Comma, Qt.Key.Key_Semicolon}:
            self.evt_separator_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class QtTagEditor(QWidget):
    """Editor for managing a collection of short text tags."""

    evt_tags_changed = Signal(list)
    evt_tag_added = Signal(str)
    evt_tag_removed = Signal(str)
    evt_text_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        placeholder: str = "Add tag...",
        *,
        flow: bool = True,
        allow_duplicates: bool = False,
        case_sensitive: bool = False,
    ) -> None:
        super().__init__(parent)
        self.allow_duplicates = allow_duplicates
        self.case_sensitive = case_sensitive
        self._tags: list[str] = []
        self._tag_widgets: dict[str, QtTagButton] = {}

        self.text_edit = _QtTagEditorLineEdit(self)
        self.text_edit.setPlaceholderText(placeholder)
        self.text_edit.setClearButtonEnabled(True)
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.returnPressed.connect(self.add_current_text)
        self.text_edit.evt_separator_pressed.connect(self.add_current_text)

        self.add_action = hp.make_action(
            self,
            "add",
            tooltip="Add the current text as a tag.",
            func=self.add_current_text,
        )
        self.text_edit.addAction(self.add_action, self.text_edit.ActionPosition.TrailingPosition)

        self.clear_action = hp.make_action(
            self,
            "clear",
            tooltip="Remove all tags.",
            func=self.clear_tags,
        )
        self.text_edit.addAction(self.clear_action, self.text_edit.ActionPosition.TrailingPosition)

        self._tag_layout = (
            hp.make_flow_layout(margin=0, horizontal_spacing=2, vertical_spacing=2)
            if flow
            else QtScrollableHLayoutWidget(self)
        )
        if not flow:
            self._tag_layout.setSpacing(2)
            self._tag_layout.set_min_height(self.text_edit.sizeHint().height())

        layout = hp.make_v_layout(spacing=4, margin=0, parent=self)
        layout.addWidget(self.text_edit)
        if flow:
            layout.addLayout(self._tag_layout)
        else:
            layout.addWidget(self._tag_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def tags(self) -> list[str]:
        """Return the current tags in display order."""
        return list(self._tags)

    def set_tags(self, tags: list[str]) -> None:
        """Replace all tags."""
        new_tags: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            normalized = self._normalize_tag(tag)
            if not normalized:
                continue
            key = self._tag_key(normalized)
            if not self.allow_duplicates and key in seen:
                continue
            seen.add(key)
            new_tags.append(normalized)

        self.clear_tags(emit_signal=False)
        for tag in new_tags:
            self._add_tag_widget(tag, emit_signal=False)
        self._emit_tags_changed()

    def add_tag(self, text: str) -> bool:
        """Add a single tag."""
        tag = self._normalize_tag(text)
        if not tag:
            return False
        if not self.allow_duplicates and self.has_tag(tag):
            return False
        self._add_tag_widget(tag, emit_signal=True)
        return True

    def add_tags(self, tags: list[str]) -> list[str]:
        """Add multiple tags and return the tags that were added."""
        added: list[str] = []
        for tag in tags:
            normalized = self._normalize_tag(tag)
            if normalized and self.add_tag(normalized):
                added.append(normalized)
        return added

    def add_current_text(self) -> list[str]:
        """Add the current input contents as one or more tags."""
        text = self.text_edit.text()
        parts = [self._normalize_tag(part) for part in re.split(r"[,;\n]+", text)]
        added = self.add_tags([part for part in parts if part])
        if added:
            with hp.qt_signals_blocked(self.text_edit):
                self.text_edit.clear()
        return added

    def remove_tag(self, text: str) -> bool:
        """Remove a tag by value."""
        key = self._find_existing_key(text)
        if key is None:
            return False

        widget = self._tag_widgets.pop(key)
        self._tags.remove(widget.text)
        self._remove_widget(widget)
        self.evt_tag_removed.emit(widget.text)
        self._emit_tags_changed()
        return True

    def clear_tags(self, emit_signal: bool = True) -> None:
        """Remove all tags."""
        for key in list(self._tag_widgets):
            widget = self._tag_widgets.pop(key)
            self._remove_widget(widget)
        self._tags.clear()
        if emit_signal:
            self._emit_tags_changed()

    def has_tag(self, text: str) -> bool:
        """Return whether the tag is present."""
        return self._find_existing_key(text) is not None

    def _add_tag_widget(self, text: str, *, emit_signal: bool) -> None:
        widget = QtTagButton(text, text, parent=self, allow_selected=False, action_type="delete", action_icon="cross")
        widget.evt_action.connect(self.remove_tag)
        self._tag_widgets[self._tag_key(text)] = widget
        self._tags.append(text)
        self._layout_add_widget(widget)
        if emit_signal:
            self.evt_tag_added.emit(text)
            self._emit_tags_changed()

    def _layout_add_widget(self, widget: QtTagButton) -> None:
        if isinstance(self._tag_layout, QtScrollableHLayoutWidget):
            self._tag_layout.addWidget(widget)
        else:
            self._tag_layout.addWidget(widget)

    def _remove_widget(self, widget: QtTagButton) -> None:
        if isinstance(self._tag_layout, QtScrollableHLayoutWidget):
            self._tag_layout.removeWidget(widget)
            return

        for index in range(self._tag_layout.count()):
            if self._tag_layout.get_widget(index) is widget:
                self._tag_layout.removeWidgetOrLayout(index)
                break

    def _on_text_changed(self, text: str) -> None:
        self.evt_text_changed.emit(text)
        if any(separator in text for separator in (",", ";", "\n")):
            self.add_current_text()

    def _emit_tags_changed(self) -> None:
        self.evt_tags_changed.emit(self.tags())

    def _normalize_tag(self, text: str) -> str:
        return text.strip()

    def _tag_key(self, text: str) -> str:
        return text if self.case_sensitive else text.casefold()

    def _find_existing_key(self, text: str) -> str | None:
        key = self._tag_key(self._normalize_tag(text))
        if key in self._tag_widgets:
            return key
        return None

    # Alias methods to offer Qt-like interface
    addTag = add_tag
    addTags = add_tags
    addCurrentText = add_current_text
    removeTag = remove_tag
    clearTags = clear_tags
    hasTag = has_tag
    setTags = set_tags
    getTags = tags
