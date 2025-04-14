"""Directory manager."""

import os
from typing import Dict, List

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp


class QtDirectoryWidget(QFrame):
    """Directory widget."""

    evt_checked = Signal(str, bool)

    def __init__(self, path: str, exist_obj_name: str = "success", parent=None):
        """Directory widget where the path is displayed alongside a couple of helpful icons/buttons.

        Parameters
        ----------
        path : str
            Path to the directory.
        exist_obj_name : str
            Specifies how the text should be displayed in case the path exists or not. For instance, it can be used to
            highlight when path exists and it should not (e.g. `warning`) or vice-versa (e.g. `success`).
        parent : QWidget, optional
            Specifies the parent of the widget.
        """
        super().__init__(parent=parent)
        self.setMinimumHeight(25)

        self.checkbox = hp.make_checkbox(self, tooltip="Click here to check item")
        self.checkbox.stateChanged.connect(self._on_check)

        self.path_label = hp.make_eliding_label2(
            self, path, elide=Qt.TextElideMode.ElideRight, tooltip="Directory path"
        )
        self.path_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.path_label.setMinimumWidth(600)

        self.new_icon = hp.make_qta_btn(self, "new", tooltip="This directory does not exist and will be created.")
        self.new_icon.setVisible(False)

        self.warning_icon = hp.make_qta_label(
            self, "warning", tooltip="This directory already exists and it should not."
        )
        self.warning_icon.setVisible(False)

        self.open_btn = hp.make_qta_btn(self, "folder", tooltip="Click here to open directory")
        self.open_btn.clicked.connect(self._on_open)

        self.edit_btn = hp.make_qta_btn(self, "edit", tooltip="Click here to edit path")
        self.edit_btn.clicked.connect(self._on_edit)
        self.edit_btn.setVisible(False)

        self.row = QHBoxLayout()
        self.row.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.row.addWidget(self.path_label, stretch=True, alignment=Qt.AlignmentFlag.AlignLeft)
        self.row.addWidget(self.new_icon)
        self.row.addWidget(self.warning_icon)
        self.row.addWidget(self.open_btn)
        self.row.addWidget(self.edit_btn)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.row)

        self._exist_obj_name = exist_obj_name
        self._not_exist_obj_name = "warning" if exist_obj_name == "success" else "success"
        self.path = path

    @property
    def is_checked(self) -> bool:
        """Flag to indicate if its checked."""
        return self.checkbox.isChecked()

    @property
    def path(self) -> str:
        """Return path."""
        return self._path

    @property
    def is_new(self) -> bool:
        """Check whether specified path will be new."""
        return not os.path.exists(self.path)

    @path.setter
    def path(self, value: str):
        self._path = value
        self.path_label.setText(value)
        self.path_label.setToolTip(self._path)
        exists = os.path.exists(value)
        obj_name = self._exist_obj_name if exists else self._not_exist_obj_name
        self.warning_icon.setVisible(obj_name == "warning")
        self.set_style(obj_name)
        self.open_btn.setVisible(exists)

    def set_style(self, object_name: str):
        """Set new style."""
        hp.update_widget_style(self.path_label, object_name)
        self.warning_icon.setVisible(object_name == "warning")

    def set_new(self, visible: bool):
        """Set visible icon."""
        self.new_icon.setVisible(visible)

    def show_as_path(self, show_full: bool):
        """Show basename without full path."""
        path = self._path if show_full else os.path.basename(self._path)
        self.path_label.setText(path)

    def _on_check(self):
        """Checked/unchecked event."""
        self.evt_checked.emit(self._path, self.checkbox.isChecked())
        hp.disable_with_opacity(self, [self.path_label], not self.checkbox.isChecked())

    def _on_edit(self):
        """Edit value."""
        new_path = hp.get_text(self, "Modify the current path...", "Modify the current path", self.path)
        if new_path is not None:
            self.path = new_path

    def _on_open(self):
        """Open directory."""
        from qtextra.utils.utilities import open_directory

        if os.path.exists(self._path):
            open_directory(self._path)


class QtDirectoryManager(QScrollArea):
    """Directory manager."""

    # triggered whenever new path is added
    evt_added = Signal(str)
    # triggered whenever path is updated
    evt_update = Signal(str)
    # triggered whenever path is removed
    evt_removed = Signal(str)

    def __init__(self, parent=None, exist_obj_name: str = "success"):
        """Directory manager.

        Parameters
        ----------
        parent : QWidget
            parent object
        exist_obj_name : str
            name of the object if the path exists. If value is `success`, then the it will be green and in case it does
            not exist, then the path will be set to `warning` and it will be rendered in red.
        """
        super().__init__(parent=parent)
        self.widgets: Dict[str, QtDirectoryWidget] = {}
        self._exist_obj_name = exist_obj_name

        scroll_widget = QWidget()
        self.setWidget(scroll_widget)

        main_layout = QVBoxLayout(scroll_widget)
        main_layout.setSpacing(2)
        main_layout.addStretch(1)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout = main_layout

    @property
    def paths(self) -> List[str]:
        """Return list of paths."""
        return list(self.widgets.keys())

    @property
    def checked_paths(self) -> List[str]:
        """Return list of paths that are checked."""
        return [widget.path for widget in self.widgets.values() if widget.is_checked]

    @property
    def n_new(self) -> int:
        """Return the total count of new directories."""
        return sum([widget.is_new for widget in self.widgets.values()])

    def clear(self):
        """Remove all directories."""
        paths = self.paths
        for path in paths:
            self.remove_path(path)

    def add_path(self, path: str):
        """Add path widget.

        Parameters
        ----------
        path : str
            path to be added to the widget
        """
        widget = QtDirectoryWidget(path, exist_obj_name=self._exist_obj_name, parent=self)
        widget.checkbox.setChecked(True)
        self.widgets[path] = widget
        self._layout.insertWidget(0, widget)
        self.evt_added.emit(path)

    def update_path(self, old_path: str, new_path: str):
        """Update path widget."""
        widget = self.widgets.pop(old_path, None)
        if widget:
            self.widgets[new_path] = widget
            self.widgets.path = new_path
            self.evt_update.emit(new_path)

    def remove_path(self, path: str):
        """Remove widget."""
        widget = self.widgets.pop(path, None)
        if widget:
            self._layout.removeWidget(widget)
            widget.deleteLater()
            self.evt_removed.emit(path)

    def validate(self, path: str, object_name: str):
        """Update style of the directory by setting its object name."""
        widget = self.widgets.get(path, None)
        if widget:
            widget.set_style(object_name)

    def set_new(self, path: str, visible: bool):
        """Update new state of the directory."""
        widget = self.widgets.get(path, None)
        if widget:
            widget.set_new(visible)

    def show_as_path(self, show_full: bool):
        """Show basename of each widget."""
        for widget in self.widgets.values():
            widget.show_as_path(show_full)

    def is_checked(self, path: str) -> bool:
        """Check whether directory is checked."""
        widget = self.widgets.get(path, None)
        if widget:
            return widget.is_checked
        return False


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        def _check():
            print(widget.checked_paths)

        import sys

        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qframe

        app, frame, ha = qframe(False)
        frame.setMinimumHeight(600)
        widget = QtDirectoryManager()
        ha.addWidget(widget)
        for i in range(3):
            widget.add_path(f"PATH {i}")

        btn = make_btn(frame, "Show")
        btn.clicked.connect(_check)
        ha.addWidget(btn)

        frame.show()
        sys.exit(app.exec_())

    _main()
