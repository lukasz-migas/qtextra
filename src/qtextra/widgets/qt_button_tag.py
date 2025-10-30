"""Pill button."""

from __future__ import annotations

import typing as ty

from koyo.secret import get_short_hash
from qtpy.QtCore import QSize, Qt, Signal, Slot  # type: ignore[attr-defined]
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_icon import QtImagePushButton
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayoutWidget

# FIXME: There is a bug that only occurs when:
#       1. Remove single widget. Dont check any of the existing widgets.
#       2. Try adding new widget - it will crash.


class QtLeftPillLabel(QLabel):
    """Left label."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)


class QtPillActionButton(QtImagePushButton):
    """Delete button."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self._mode = self._icon = "delete"
        self.mode = self.icon = "delete"

    @property
    def icon(self) -> str:
        """Get icon."""
        return self._icon

    @icon.setter
    def icon(self, value: str):
        """Set icon."""
        self._icon = value
        self.set_qta(value)

    @property
    def mode(self) -> str:
        """Get mode."""
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._mode = value
        self.setProperty("mode", value)
        hp.polish_widget(self)


class QtTagButton(QFrame):
    """Two-sided pill button.

    The left side is used to show text of some kind and the right has delete button
    """

    evt_action = Signal(str)
    evt_clicked = Signal(str)
    evt_checked = Signal(str, bool)
    _active: bool = False

    def __init__(
        self,
        label: str,
        hash_id: str,
        parent: QWidget | None = None,
        allow_action: bool = True,
        action_type: str = "delete",
        action_icon: str = "cross",
        allow_selected: bool = True,
        hide_check: bool = False,
    ):
        super().__init__(parent=parent)
        self.setMaximumHeight(28)
        self.setMouseTracking(True)
        self.hash_id = hash_id
        self.hide_check = hide_check
        self._allow_selected = allow_selected
        self._label = label
        if hide_check:
            self.setProperty("hide_check", "True")

        self.selected = hp.make_qta_label(self, "check")
        self.selected.set_small()
        if not self._allow_selected:
            self.selected.evt_clicked.connect(self._handle_click)
        self.selected.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        self.label = QtLeftPillLabel(parent=self, text=label)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        if not label:
            self.label.setVisible(False)

        self.action_btn = QtPillActionButton(parent=self)
        self.action_btn.set_xsmall()
        self.action_btn.clicked.connect(self._on_action)
        self.action_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        self.action_btn.setVisible(allow_action)
        self.action_btn.icon = action_icon
        self.action_btn.mode = action_type
        self.setProperty("mode", action_type)
        hp.polish_widget(self.action_btn)

        layout = QHBoxLayout(self)
        layout.addWidget(self.selected, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter, stretch=True)
        if allow_action:
            layout.addWidget(hp.make_v_line(self))
        layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        self.label.adjustSize()
        self.action_btn.adjustSize()
        self.adjustSize()

        self.active = self._active

    @property
    def text(self) -> str:
        """Get name of the tag."""
        return self.label.text()

    @text.setter
    def text(self, value: str) -> None:
        self.label.setText(value)
        self.label.setVisible(len(value) > 0)

    @property
    def active(self) -> bool:
        """Get checked state."""
        return self._active

    @active.setter
    def active(self, state: bool) -> None:
        self.setProperty("active", str(state))
        self.selected.setVisible(False if self.hide_check else state)
        hp.polish_widget(self)
        self._active = state
        self.evt_checked.emit(self.hash_id, state)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Process mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._allow_selected:
                self.active = not self._active
            else:
                self._handle_click()
        super().mousePressEvent(event)

    def _handle_click(self) -> None:
        self.evt_clicked.emit(self.hash_id)

    def sizeHint(self) -> QSize:
        """Get size hint."""
        sh = self.selected.sizeHint() + self.label.sizeHint()
        sh += self.action_btn.sizeHint() if self.action_btn.isVisible() else QSize(0, 0)
        return sh

    def _on_action(self) -> None:
        """On delete."""
        self.evt_action.emit(self.hash_id)


class QtTagManager(QWidget):
    """Manager class that contains multiple QtTagButtons."""

    evt_changed = Signal(str, bool)
    evt_checked = Signal(list)
    evt_clicked = Signal(str)
    evt_plus_clicked = Signal()

    # Widgets
    _plus_btn = None
    _clear_btn = None
    _filter_edit = None

    def __init__(
        self,
        parent: QWidget | None = None,
        allow_action: bool = False,
        flow: bool = True,
    ):
        super().__init__(parent=parent)
        self.allow_action = allow_action
        self.case_sensitive = False

        layout = hp.make_h_layout(parent=self, margin=0, spacing=0)
        self._layout = (
            hp.make_flow_layout(horizontal_spacing=1, vertical_spacing=1, margin=0)
            if flow
            else QtScrollableHLayoutWidget()
        )
        if flow:
            layout.addLayout(self._layout)
        else:
            self._layout.setSpacing(2)
            layout.addWidget(self._layout)

        self._action_layout = hp.make_h_layout(margin=(2, 0, 0, 0), spacing=0)
        layout.addLayout(self._action_layout)

        self._layout.setSpacing(2)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self.widgets: dict[str, QtTagButton] = {}
        self.buttons: dict[str, QWidget] = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add_tag(
        self,
        text: str,
        hash_id: str | None = None,
        allow_action: bool | None = None,
        active: bool = False,
        allow_check: bool = True,
        hide_check: bool = False,
        set_property: bool = False,
    ) -> str:
        """Add tag to the Tag manager.."""
        if not hash_id:
            hash_id = get_short_hash()
        allow_action = self.allow_action if allow_action is None else allow_action
        widget = QtTagButton(
            text,
            hash_id,
            allow_action=allow_action,
            parent=self,
            allow_selected=allow_check,
            hide_check=hide_check,
        )
        widget.active = active
        widget.evt_action.connect(self.remove_tag)
        widget.evt_checked.connect(self._tag_changed)
        widget.evt_clicked.connect(self.evt_clicked.emit)
        if set_property:
            hp.set_properties(widget, {"text": text})

        self._layout.addWidget(widget)
        self.widgets[hash_id] = widget
        self._handle_filter_by()
        return hash_id

    def add_tags(
        self,
        options: list[str],
        allow_action: bool | None = None,
        allow_check: bool = True,
        hide_check: bool = False,
        set_property: bool = False,
    ) -> None:
        """Add tags."""
        for tag in options:
            self.add_tag(tag, allow_action=allow_action, allow_check=allow_check, hide_check=hide_check, set_property=set_property)

    @Slot(str)  # type: ignore[misc]
    def remove_tag(self, hash_id: str) -> None:
        """Remove tag."""
        widget = self.widgets.pop(hash_id, None)
        if widget:
            hp.disconnect_event(widget, "evt_action", self.remove_tag)
            hp.disconnect_event(widget, "evt_checked", self._tag_changed)
            self._layout.removeWidget(widget)
            widget.deleteLater()

    def remove_tags(self) -> None:
        """Clear all options."""
        for widget in self.widgets.values():
            widget.deleteLater()
        self.widgets.clear()

    def update_label(self, hash_id: str, new_label: str) -> None:
        """Update label of specified tag."""
        tag = self.widgets[hash_id]
        tag.text = new_label

    def add_button(self, icon_name: str, tooltip: str = "") -> QtImagePushButton:
        """Add button."""
        button = hp.make_qta_btn(self, icon_name, tooltip=tooltip, small=True, standout=True)
        self._action_layout.addWidget(button)
        self.buttons[icon_name] = button
        return button

    def add_plus(self) -> QtImagePushButton:
        """Add plus button."""
        if self._plus_btn is not None:
            raise ValueError("Add button already exists.")

        self._plus_btn = self.add_button("add")
        self._plus_btn.clicked.connect(self._handle_add_click)
        return self._plus_btn

    def _handle_add_click(self) -> None:
        """Handle add click."""
        text = hp.get_text(self, "Type-in new label.", "New label")
        if text:
            self.add_tag(text, allow_action=self.allow_action)
            self.evt_plus_clicked.emit()

    def add_clear(self) -> QtImagePushButton:
        """Add plus button."""
        if self._clear_btn is not None:
            raise ValueError("Clear button already exists.")

        self._clear_btn = self.add_button("cross")
        self._clear_btn.clicked.connect(self.clear_selection)
        return self._clear_btn

    def add_filter(
        self, placeholder: str = "Type-in tag name...", max_width: int = 150, case_sensitive: bool = False
    ) -> None:
        """Add filter."""
        if self._filter_edit is not None:
            raise ValueError("Filter edit already exists.")

        self.case_sensitive = case_sensitive
        self._filter_edit = hp.make_line_edit(
            self, placeholder=placeholder, func_changed=self._handle_filter_by, func_clear=self._handle_filter_by
        )
        if max_width:
            self._filter_edit.setMaximumWidth(max_width)
        self._action_layout.addWidget(self._filter_edit)

    def _handle_filter_by(self) -> None:
        if self._filter_edit is None:
            return

        if self.case_sensitive:
            self._handle_case_sensitive_filter_by()
        else:
            self._handle_case_insensitive_filter_by()

    def _handle_case_sensitive_filter_by(self) -> None:
        text = self._filter_edit.text()
        for widget in self.widgets.values():
            widget.setHidden(text not in widget.text)

    def _handle_case_insensitive_filter_by(self) -> None:
        text = self._filter_edit.text().lower()
        for widget in self.widgets.values():
            widget.setHidden(text not in widget.text.lower())

    @Slot(str, bool)  # type: ignore[misc]
    def _tag_changed(self, hash_id: str, state: bool) -> None:
        """Tag was checked or unchecked."""
        self.evt_changed.emit(hash_id, state)
        self.evt_checked.emit(self.selected_options)

    @property
    def selected_ids(self) -> list[str]:
        """Get list of selected tags."""
        selected = []
        for hash_id, tag in self.widgets.items():
            if tag.active:
                selected.append(hash_id)
        return selected

    @property
    def selected_options(self) -> list[str]:
        """Get list of selected tags."""
        selected = []
        for _hash_id, tag in self.widgets.items():
            if tag.active:
                selected.append(tag.text)
        return selected

    def clear_selection(self) -> None:
        """Clear selections."""
        for widget in self.widgets.values():
            if widget.active:
                widget.active = False

    # Alias methods to offer Qt-like interface
    addTag = add_tag
    addTags = add_tags
    removeTag = remove_tag
    removeTags = remove_tags
    clearSelection = clear_selection
    updateLabel = update_label
    addButton = add_button
    addPlus = add_plus
    addClear = add_clear


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, va = qframe(False)
        frame.setMinimumSize(400, 400)

        mgr = QtTagManager(allow_action=True)
        for i in range(5):
            mgr.add_tag(f"Tag number: {i}")
        mgr.add_filter()
        mgr.add_plus()
        mgr.add_tag("Tag number: 10", allow_check=False)
        va.addWidget(mgr, stretch=True)

        mgr = QtTagManager(allow_action=False)
        for i in range(5):
            mgr.add_tag(f"Tag number: {i}", hide_check=False)
        mgr.add_plus()
        mgr.add_tag("Tag number: 10", allow_check=False)
        va.addWidget(mgr, stretch=True)

        mgr = QtTagManager(allow_action=False, flow=False)
        for i in range(5):
            mgr.add_tag(f"Tag number: {i}")
        mgr.add_filter()
        mgr.add_plus()
        mgr.add_clear()
        mgr.add_tag("Tag number: 10", allow_check=False)
        va.addWidget(mgr, stretch=True)

        widget = QtTagButton("Tag 1", "TEST", frame)
        va.addWidget(widget)
        widget = QtTagButton("Much longer label", "TEST", frame)
        va.addWidget(widget, stretch=True)
        widget = QtTagButton("And this is even longer label", "TEST", frame)
        va.addWidget(widget, stretch=True)

        frame.show()
        sys.exit(app.exec_())

    _main()
