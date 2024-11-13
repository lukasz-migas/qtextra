"""Mini toolbar."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_image_button import QtImagePushButton


class QtMiniToolbar(QFrame):
    """Mini toolbar."""

    def __init__(
        self,
        parent: QWidget | None,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        add_spacer: bool = True,
        icon_size: ty.Literal["small", "average", "medium", "normal"] | str | None = None,
        spacing: int = 0,
    ):
        super().__init__(parent)
        self._tools: dict[str, QtImagePushButton] = {}
        self.orientation = orientation

        self.layout_ = QHBoxLayout(self) if orientation == Qt.Orientation.Horizontal else QVBoxLayout(self)
        if add_spacer:
            self.layout_.addSpacerItem(
                hp.make_h_spacer() if orientation == Qt.Orientation.Horizontal else hp.make_v_spacer()
            )
        self.layout_.setSpacing(spacing)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.max_size = 28
        self.icon_object_name, self.icon_size = (
            QtImagePushButton.get_icon_size_for_name(icon_size) if icon_size else None,
            None,
        )

    @property
    def max_size(self) -> int:
        """Return maximum size."""
        return self.maximumHeight() if self.orientation == Qt.Orientation.Horizontal else self.maximumWidth()

    @max_size.setter
    def max_size(self, value: int) -> None:
        self.setMaximumHeight(value) if self.orientation == Qt.Orientation.Horizontal else self.setMaximumWidth(value)

    @property
    def n_items(self) -> int:
        """Return the number of items in the layout."""
        return self.layout_.count()

    def _make_qta_button(
        self,
        name: str,
        func: ty.Callable | None = None,
        func_menu: ty.Callable | None = None,
        tooltip: str | None = None,
        checkable: bool = False,
        check: bool = False,
        size: tuple[int, int] | None = None,
        flat: bool = False,
        small: bool = False,
        medium: bool = False,
        average: bool = False,
        normal: bool = False,
        checked_icon_name: ty.Optional[str] = None,
        object_name: str | None = None,
    ) -> QtImagePushButton:
        if self.icon_size:
            size = self.icon_size
            object_name = self.icon_object_name
        if not any((small, average, medium, normal)) and not size:
            size = (26, 26)
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already exists.")
        btn = hp.make_qta_btn(
            self,
            name,
            tooltip=tooltip,
            flat=flat,
            medium=medium,
            size=size,
            checkable=checkable,
            checked=check,
            func=func,
            func_menu=func_menu,
            small=small,
            average=average,
            normal=normal,
            checked_icon_name=checked_icon_name,
            object_name=object_name,
        )
        self._tools[name] = btn
        return btn

    def add_button(self, button: QtImagePushButton) -> QtImagePushButton:
        """Add any button the toolbar."""
        self.layout_.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        return button

    def add_widget(self, widget: QWidget, stretch: bool = False) -> QWidget:
        """Insert any widget at specified position."""
        self.layout_.addWidget(
            widget,
            alignment=Qt.AlignmentFlag.AlignCenter if not stretch else Qt.AlignmentFlag.AlignLeft,
            stretch=stretch,
        )
        return widget

    def add_layout(self, layout: QLayout) -> QLayout:
        """Insert any layout at specified position."""
        self.layout_.addLayout(layout)
        return layout

    def add_qta_tool(
        self,
        name: str,
        func: ty.Callable | None = None,
        tooltip: str | None = None,
        checkable: bool = False,
        check: bool = False,
        size: tuple[int, int] | None = None,
        small: bool = False,
        average: bool = False,
    ) -> QtImagePushButton:
        """Insert tool."""
        btn = self._make_qta_button(
            name,
            func=func,
            tooltip=tooltip,
            checkable=checkable,
            check=check,
            size=size,
            small=small,
            average=average,
        )
        self.add_button(btn)
        return btn

    def insert_button(self, button: QtImagePushButton, index: int = 0, set_size: bool = True) -> QtImagePushButton:
        """Insert any button at specified position."""
        if hasattr(button, "set_size") and set_size:
            button.set_size((26, 26))
        self.layout_.insertWidget(index, button, alignment=Qt.AlignmentFlag.AlignCenter)
        return button

    def insert_widget(self, widget: QWidget, index: int = 0) -> QWidget:
        """Insert any widget at specified position."""
        self.layout_.insertWidget(index, widget, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    def insert_layout(self, layout: QLayout, index: int = 0) -> QLayout:
        """Insert any layout at specified position."""
        self.layout_.insertLayout(index, layout)
        return layout

    def insert_qta_tool(
        self,
        name: str,
        flat: bool = False,
        func: ty.Callable | None = None,
        func_menu: ty.Callable | None = None,
        tooltip: str | None = None,
        checkable: bool = False,
        check: bool = False,
        size: tuple[int, int] | None = None,
        small: bool = False,
        average: bool = False,
        normal: bool = False,
        hidden: bool = False,
        checked_icon_name: ty.Optional[str] = None,
    ) -> QtImagePushButton:
        """Insert tool."""
        btn = self._make_qta_button(
            name,
            flat=flat,
            func=func,
            func_menu=func_menu,
            tooltip=tooltip,
            checkable=checkable,
            check=check,
            size=size,
            small=small,
            average=average,
            normal=normal,
            checked_icon_name=checked_icon_name,
        )
        self.insert_button(btn)
        if hidden:
            btn.hide()
        return btn

    def insert_separator(self) -> None:
        """Insert horizontal or vertical separator."""
        sep = hp.make_v_line() if self.orientation == Qt.Orientation.Horizontal else hp.make_h_line(self)
        self.layout_.insertWidget(0, sep)

    def insert_spacer(self) -> None:
        """Insert spacer item."""
        spacer = (
            hp.make_spacer_widget()
        )  # make_v_spacer() if self.orientation == Qt.Orientation.Horizontal else make_h_spacer()
        self.layout_.insertWidget(0, spacer, stretch=True)

    def append_spacer(self) -> None:
        """Insert spacer item."""
        spacer = (
            hp.make_spacer_widget()
        )  # make_v_spacer() if self.orientation == Qt.Orientation.Horizontal else make_h_spacer()
        self.layout_.insertWidget(self.layout_.count(), spacer, stretch=True)

    def show_border(self) -> None:
        """Show border."""
        self.setFrameShape(QFrame.Shape.Box)

    def swap_orientation(self) -> None:
        """Swap orientation."""
        self.orientation = (
            QHBoxLayout.Direction.LeftToRight
            if self.orientation == Qt.Orientation.Vertical
            else QVBoxLayout.Direction.TopToBottom
        )
        self.layout_.setDirection(self.orientation)
        self.layout_.invalidate()
        self.layout_.update()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    frame = QWidget()
    ha = QHBoxLayout()
    frame.setLayout(ha)

    h = QtMiniToolbar(None, orientation=Qt.Orientation.Horizontal)

    v = QtMiniToolbar(None, orientation=Qt.Orientation.Vertical)

    ha.addWidget(h)
    ha.addWidget(v)
    frame.show()
    sys.exit(app.exec_())
