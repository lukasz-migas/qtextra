"""Pill button."""
from typing import Dict

from koyo.secret import get_short_hash
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_flow_layout import QtFlowLayout
from qtextra.widgets.qt_image_button import QtImagePushButton

# FIXME: There is a bug that only occurs when:
#       1. Remove single widget. Dont check any of the existing widgets.
#       2. Try adding new widget - it will crash.


class QtLeftPillLabel(QLabel):
    """Left label."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QtPillActionButton(QtImagePushButton):
    """Delete button."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mode = "delete"
        self.mode = "delete"

    @property
    def mode(self):
        """Get mode."""
        return self._mode

    @mode.setter
    def mode(self, action_type: str):
        self._mode = action_type
        self.set_qta(action_type)
        self.setProperty("mode", action_type)
        hp.polish_widget(self)


class QtTagButton(QFrame):
    """Two-sided pill button.

    The left side is used to show text of some kind and the right has delete button
    """

    evt_action = Signal(str)
    evt_clicked = Signal()
    evt_checked = Signal(str, bool)
    _active: bool = False

    def __init__(
        self,
        label: str,
        hash_id: str,
        parent=None,
        allow_action: bool = True,
        action_type: str = "delete",
        allow_selected: bool = True,
    ):
        super().__init__(parent=parent)
        self.setMaximumHeight(28)
        self.setMouseTracking(True)
        self.hash_id = hash_id
        self._allow_selected = allow_selected
        self._label = label

        self.selected = hp.make_qta_label(self, "check")
        self.selected.set_small()
        if not self._allow_selected:
            self.selected.evt_clicked.connect(self.evt_clicked.emit)
        self.selected.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        self.label = QtLeftPillLabel(parent=self, text=label)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        if not label:
            self.label.setVisible(False)

        self.action_btn = QtPillActionButton(parent=self)
        self.action_btn.set_small()
        self.action_btn.clicked.connect(self._on_action)
        self.action_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        self.action_btn.setVisible(allow_action)
        self.action_btn.mode = action_type
        self.setProperty("mode", action_type)
        hp.polish_widget(self.action_btn)

        layout = QHBoxLayout()
        layout.addWidget(self.selected)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter, stretch=True)
        layout.addWidget(self.action_btn)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        self.label.adjustSize()
        self.action_btn.adjustSize()
        self.adjustSize()

        self.active = self._active

    @property
    def tag(self) -> str:
        """Get name of the tag."""
        return self.label.text()

    @tag.setter
    def tag(self, value: str):
        self.label.setText(value)
        self.label.setVisible(len(value) > 0)

    @property
    def active(self) -> bool:
        """Get checked state."""
        return self._active

    @active.setter
    def active(self, state: bool):
        self.setProperty("active", str(state))
        self.selected.setVisible(state)
        hp.polish_widget(self)
        self._active = state
        self.evt_checked.emit(self.hash_id, state)

    def mousePressEvent(self, event):
        """Process mouse press event."""
        if event.button() == Qt.LeftButton:
            if self._allow_selected:
                self.active = not self._active
            else:
                self.evt_clicked.emit()
        super().mousePressEvent(event)

    def sizeHint(self):
        """Get size hint."""
        sh = self.selected.sizeHint() + self.label.sizeHint()
        sh += self.action_btn.sizeHint() if self.action_btn.isVisible() else QSize(0, 0)
        return sh

    def _on_action(self):
        """On delete."""
        self.evt_action.emit(self.hash_id)


class QtTagManager(QWidget):
    """Manager class that contains multiple QtTagButtons."""

    evt_changed = Signal(str, bool)
    evt_plus_clicked = Signal()
    _action_btn = None

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._layout = QtFlowLayout(self)
        self.widgets: Dict[str, QtTagButton] = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add_tag(
        self,
        text: str,
        hash_id: str = None,
        allow_action: bool = False,
        active: bool = False,
        allow_selected: bool = True,
    ) -> str:
        """Add tag to ."""
        if not hash_id:
            hash_id = get_short_hash()
        widget = QtTagButton(text, hash_id, allow_action=allow_action, parent=self, allow_selected=allow_selected)
        widget.active = active
        widget.evt_action.connect(self.remove_tag)
        widget.evt_checked.connect(self._tag_changed)

        if self._action_btn is None:
            self._layout.addWidget(widget)
        else:
            self._layout.insertWidget(len(self.widgets), widget)
        self.widgets[hash_id] = widget
        return hash_id

    @Slot(str)
    def remove_tag(self, hash_id: str):
        """Remove tag."""
        widget = self.widgets.pop(hash_id, None)
        if widget:
            hp.disconnect_event(widget, "evt_action", self.remove_tag)
            hp.disconnect_event(widget, "evt_checked", self._tag_changed)
            self._layout.removeWidget(widget)
            widget.deleteLater()

    def update_label(self, hash_id: str, new_label: str):
        """Update label of specified tag."""
        tag = self.widgets[hash_id]
        tag.tag = new_label

    def add_button(self, object_type: str, tooltip: str = ""):
        """Add button."""
        self._action_btn = hp.make_qta_btn(self, object_type, tooltip=tooltip)
        self._layout.addWidget(self._action_btn)
        return self._action_btn

    def add_plus(self):
        """Add plus button."""
        self.add_button("plus")
        self._action_btn.clicked.connect(self.on_add_click)

    def on_add_click(self):
        """Handle add click."""
        text = hp.get_text(self, "Type-in new label.", "New label")
        if text:
            self.add_tag(text)
            self.evt_plus_clicked.emit()

    @Slot(str, bool)
    def _tag_changed(self, hash_id: str, state: bool):
        """Tag was checked or unchecked."""
        self.evt_changed.emit(hash_id, state)

    @property
    def selected(self):
        """Get list of selected tags."""
        selected = []
        for hash_id, tag in self.widgets.items():
            if tag.active:
                selected.append(hash_id)
        return selected


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, va = qframe(False)
        frame.setMinimumSize(400, 400)

        mgr = QtTagManager()
        for i in range(5):
            mgr.add_tag(f"Tag number: {i}", allow_action=True)
        mgr.add_plus()
        mgr.add_tag("Tag number: 10", allow_action=False, allow_selected=False)

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
