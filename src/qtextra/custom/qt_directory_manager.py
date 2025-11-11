"""Directory manager."""

from __future__ import annotations

from pathlib import Path

from koyo.typing import PathLike
from qtpy.QtCore import Qt, Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFrame, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp

SuccessObjName = "success_path"
WarningObjName = "warning_path"


class DirectoryMessages:
    """Directory messages."""

    EXISTS = "This directory already exists and it should not."
    WILL_BE_CREATED = "This directory does not exist and will be created."


class QtDirectoryWidget(QFrame):
    """Directory widget."""

    evt_checked = Signal(Path, bool)

    def __init__(self, path: PathLike, exist_obj_name: str = SuccessObjName, parent: QWidget | None = None):
        """Directory widget where the path is displayed alongside a couple of helpful icons/buttons.

        Parameters
        ----------
        path : PathLike
            Path to the directory.
        exist_obj_name : str
            Specifies how the text should be displayed in case the path exists or not. For instance, it can be used to
            highlight when a path exists and it should not (e.g. `warning`) or vice-versa (e.g. `success`).
        parent : QWidget, optional
            Specifies the parent of the widget.
        """
        super().__init__(parent=parent)
        self.setMinimumHeight(25)

        self.checkbox = hp.make_checkbox(self, tooltip="Click here to check item", func=self._on_check)

        self.path_label = hp.make_eliding_label2(
            self, str(path), elide=Qt.TextElideMode.ElideRight, tooltip="Directory path"
        )
        self.path_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.path_label.setMinimumWidth(600)
        # self.path_label = hp.make_label(self, str(path), elide=Qt.TextElideMode.ElideLeft, tooltip="Directory path")
        # self.path_label.setMinimumWidth(600)

        self.new_icon = hp.make_tooltip_label(
            self,
            "new",
            tooltip=DirectoryMessages.WILL_BE_CREATED if exist_obj_name == SuccessObjName else DirectoryMessages.EXISTS,
            hide=True,
            normal=True,
            retain_size=True,
        )

        self.warning_icon = hp.make_warning_label(
            self,
            tooltip=DirectoryMessages.EXISTS if exist_obj_name == WarningObjName else DirectoryMessages.WILL_BE_CREATED,
            hide=True,
            normal=True,
            retain_size=True,
        )

        self.open_btn = hp.make_qta_btn(self, "folder", tooltip="Click here to open directory", func=self._on_open)
        self.edit_btn = hp.make_qta_btn(self, "edit", tooltip="Click here to edit path", func=self._on_edit, hide=True)

        self.row = hp.make_h_layout(parent=self, margin=0, spacing=1)
        self.row.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.row.addWidget(self.new_icon)
        self.row.addWidget(self.warning_icon)
        self.row.addWidget(self.path_label, stretch=True, alignment=Qt.AlignmentFlag.AlignLeft)
        self.row.addWidget(self.open_btn)
        self.row.addWidget(self.edit_btn)

        self._exist_obj_name = exist_obj_name
        self._not_exist_obj_name = WarningObjName if exist_obj_name == SuccessObjName else SuccessObjName
        self.path = path

    @property
    def is_checked(self) -> bool:
        """Flag to indicate if its checked."""
        return self.checkbox.isChecked()

    @property
    def path(self) -> Path:
        """Return path."""
        return self._path

    @path.setter
    def path(self, value: str | Path) -> None:
        self._path = Path(value)
        self.path_label.setText(str(self._path))
        self.path_label.setToolTip(str(self._path))
        exists = Path(value).exists()
        obj_name = self._exist_obj_name if exists else self._not_exist_obj_name
        self.warning_icon.setVisible(obj_name == WarningObjName)
        self.set_style(obj_name)
        self.open_btn.setVisible(exists)

    @property
    def is_new(self) -> bool:
        """Check whether the specified path will be new."""
        return not self.path.exists()

    def set_style(self, object_name: str) -> None:
        """Set a new style."""
        hp.update_widget_style(self.path_label, object_name)
        self.warning_icon.setVisible(object_name == WarningObjName)

    def set_new(self, visible: bool) -> None:
        """Set visible icon."""
        self.new_icon.setVisible(visible)

    def show_as_path(self, show_full: bool) -> None:
        """Show basename without the full path."""
        path = self._path if show_full else Path(self._path).parent
        self.path_label.setText(str(path))

    def _on_check(self) -> None:
        """Checked/unchecked event."""
        self.evt_checked.emit(self.path, self.checkbox.isChecked())
        hp.disable_with_opacity(self, [self.path_label], not self.checkbox.isChecked())

    def _on_edit(self) -> None:
        """Edit value."""
        new_path = hp.get_text(self, "Modify the current path...", "Modify the current path", str(self.path))
        if new_path is not None:
            self.path = new_path

    def _on_open(self) -> None:
        """Open the directory."""
        from koyo.path import open_directory_alt

        if Path(self._path):
            open_directory_alt(self._path)


class QtDirectoryManager(QScrollArea):
    """Directory manager."""

    # triggered whenever a new path is added
    evt_added = Signal(Path)
    # triggered whenever a path is updated
    evt_update = Signal(Path)
    # triggered whenever a path is removed
    evt_removed = Signal(Path)

    def __init__(self, parent: QWidget | None = None, exist_obj_name: str = SuccessObjName):
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
        self.widgets: dict[Path, QtDirectoryWidget] = {}
        self._exist_obj_name = exist_obj_name

        scroll_widget = QWidget()
        self.setWidget(scroll_widget)

        main_layout = QVBoxLayout(scroll_widget)
        main_layout.setSpacing(2)
        main_layout.addStretch(1)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout = main_layout

    @property
    def paths(self) -> list[Path]:
        """Return list of paths."""
        return list(self.widgets.keys())

    @property
    def checked_paths(self) -> list[Path]:
        """Return the list of paths that are checked."""
        return [widget.path for widget in self.widgets.values() if widget.is_checked]

    @property
    def n_new(self) -> int:
        """Return the total count of new directories."""
        return sum([widget.is_new for widget in self.widgets.values()])

    def clear(self) -> None:
        """Remove all directories."""
        paths = self.paths
        for path in paths:
            self.remove_path(path)

    def add_path(self, path: PathLike) -> None:
        """Add the path widget.

        Parameters
        ----------
        path : str
            path to be added to the widget
        """
        widget = QtDirectoryWidget(path, exist_obj_name=self._exist_obj_name, parent=self)
        widget.checkbox.setChecked(True)
        self.widgets[widget.path] = widget
        self._layout.insertWidget(0, widget)
        self.evt_added.emit(widget.path)

    def update_path(self, old_path: PathLike, new_path: PathLike) -> None:
        """Update path widget."""
        old_path = Path(old_path)
        widget = self.widgets.pop(old_path, None)
        if widget:
            widget.path = new_path
            self.widgets[widget.path] = widget
            self.evt_update.emit(widget.path)

    def remove_path(self, path: PathLike) -> None:
        """Remove the widget."""
        path = Path(path)
        widget = self.widgets.pop(path, None)
        if widget:
            self._layout.removeWidget(widget)
            widget.deleteLater()
            self.evt_removed.emit(path)

    def validate(self, path: PathLike, object_name: str) -> None:
        """Update the style of the directory by setting its object name."""
        path = Path(path)
        widget = self.widgets.get(path, None)
        if widget:
            widget.set_style(object_name)

    def set_new(self, path: PathLike, visible: bool) -> None:
        """Update the state of the directory."""
        path = Path(path)
        widget = self.widgets.get(path, None)
        if widget:
            widget.set_new(visible)

    def show_as_path(self, show_full: bool) -> None:
        """Show the basename of each widget."""
        for widget in self.widgets.values():
            widget.show_as_path(show_full)

    def is_checked(self, path: PathLike) -> bool:
        """Check whether the directory is checked."""
        path = Path(path)
        widget = self.widgets.get(path, None)
        if widget:
            return widget.is_checked
        return False


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        def _check() -> None:
            print(widget.checked_paths)

        import sys

        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qframe

        app, frame, ha = qframe(False)
        frame.setMinimumHeight(600)
        widget = QtDirectoryManager()
        ha.addWidget(widget)
        for _i in range(3):
            widget.add_path(Path.cwd().resolve())
        widget.add_path(Path.cwd().resolve() / "non-existing-dir")
        widget.add_path("non-existing-path")

        btn = make_btn(frame, "Show")
        btn.clicked.connect(_check)
        ha.addWidget(btn)

        frame.show()
        sys.exit(app.exec_())

    _main()  # type: ignore[no-untyped-call]
