"""Mini toolbar."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.typing import Orientation
from qtextra.widgets.qt_button_icon import QtImagePushButton


class QtMiniToolbar(QFrame):
    """Mini toolbar."""

    def __init__(
        self,
        parent: QWidget | None,
        orientation: Orientation | Qt.Orientation = Qt.Orientation.Horizontal,
        add_spacer: bool = True,
        icon_size: ty.Literal["small", "average", "medium", "normal"] | str | None = None,
        spacing: int = 0,
    ):
        super().__init__(parent)
        self._tools: dict[str, QtImagePushButton] = {}
        self.orientation = hp.get_orientation(orientation)

        self.layout_ = QHBoxLayout(self) if self.orientation == Qt.Orientation.Horizontal else QVBoxLayout(self)
        self.layout_.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_.setSpacing(spacing)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        if add_spacer:
            self.layout_.addSpacerItem(
                hp.make_h_spacer() if self.orientation == Qt.Orientation.Horizontal else hp.make_v_spacer()
            )

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
        current_max = self.max_size
        if current_max == value:
            return
        self.setMaximumHeight(value) if self.orientation == Qt.Orientation.Horizontal else self.setMaximumWidth(value)

    def _update_max_size(self, widget: QWidget, padding: int = 4):
        self.max_size = (
            widget.sizeHint().height() if self.orientation == Qt.Orientation.Horizontal else widget.sizeHint().width()
        ) + padding

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
        is_menu: bool = False,
        hide: bool = False,
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
            hide=hide,
            is_menu=is_menu,
        )
        self._tools[name] = btn
        return btn

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
        normal: bool = False,
        is_menu: bool = False,
        hide: bool = False,
        func_menu: ty.Callable | None = None,
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
            normal=normal,
            is_menu=is_menu,
            hide=hide,
            func_menu=func_menu,
        )
        self.add_button(btn)
        return btn

    def add_layout(self, layout: QLayout) -> QLayout:
        """Insert any layout at specified position."""
        self.layout_.addLayout(layout)
        return layout

    def insert_layout(self, layout: QLayout, index: int = 0) -> QLayout:
        """Insert any layout at specified position."""
        self.layout_.insertLayout(index, layout)
        return layout

    def add_button(self, button: QtImagePushButton, set_size: bool = True) -> QtImagePushButton:
        """Add any button to the toolbar."""
        if hasattr(button, "set_qta_size") and set_size:
            button.set_qta_size((26, 26))
        self.layout_.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        self._update_max_size(button)
        return button

    def insert_button(self, button: QtImagePushButton, index: int = 0, set_size: bool = True) -> QtImagePushButton:
        """Insert any button at specified position."""
        if hasattr(button, "set_qta_size") and set_size:
            button.set_qta_size((26, 26))
        self.layout_.insertWidget(index, button, alignment=Qt.AlignmentFlag.AlignCenter)
        self._update_max_size(button)
        return button

    def add_widget(self, widget: QWidget, stretch: bool = False) -> QWidget:
        """Insert any widget at specified position."""
        kws = {}
        if not stretch:
            kws["alignment"] = Qt.AlignmentFlag.AlignCenter
        self.layout_.addWidget(widget, stretch=stretch, **kws)
        self._update_max_size(widget)
        return widget

    def insert_widget(self, widget: QWidget, index: int = 0) -> QWidget:
        """Insert any widget at specified position."""
        self.layout_.insertWidget(index, widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self._update_max_size(widget)
        return widget

    def insert_qta_tool(
        self,
        name: str,
        index: int = 0,
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
        self.insert_button(btn, index)
        if hidden:
            btn.hide()
        return btn

    def add_separator(self) -> None:
        """Add separator."""
        sep = hp.make_v_line() if self.orientation == Qt.Orientation.Horizontal else hp.make_h_line(self)
        self.layout_.addWidget(sep)

    def insert_separator(self) -> None:
        """Insert horizontal or vertical separator."""
        sep = hp.make_v_line() if self.orientation == Qt.Orientation.Horizontal else hp.make_h_line(self)
        self.layout_.insertWidget(0, sep)

    def insert_spacer(self) -> None:
        """Insert spacer item."""
        spacer = (
            hp.make_horizontal_spacer() if self.orientation == Qt.Orientation.Horizontal else hp.make_vertical_spacer()
        )
        self.layout_.insertWidget(0, spacer, stretch=True)

    def add_spacer(self) -> None:
        """Insert spacer item."""
        spacer = (
            hp.make_horizontal_spacer() if self.orientation == Qt.Orientation.Horizontal else hp.make_vertical_spacer()
        )
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

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)

    wdg = QtMiniToolbar(None, orientation=Qt.Orientation.Horizontal)
    for icon in ["home", "settings", "help", "info", "warning", "error"]:
        wdg.add_qta_tool(icon, tooltip=icon, func=None)
    ha.addWidget(wdg)

    wdg = QtMiniToolbar(None, orientation=Qt.Orientation.Vertical)
    for icon in ["home", "settings", "help", "info", "warning", "error"]:
        wdg.add_qta_tool(icon, tooltip=icon, func=None)
    ha.addWidget(wdg)
    frame.show()
    sys.exit(app.exec_())
