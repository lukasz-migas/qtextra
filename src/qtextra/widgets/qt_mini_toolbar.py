"""Mini toolbar."""
import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp


class QtMiniToolbar(QFrame):
    """Mini toolbar."""

    def __init__(self, parent, orientation: Qt.Orientation = Qt.Orientation.Horizontal, add_spacer: bool = True):
        super().__init__(parent)
        self._tools = {}
        self.orientation = orientation

        self.layout_ = QHBoxLayout(self) if orientation == Qt.Orientation.Horizontal else QVBoxLayout(self)
        if add_spacer:
            self.layout_.addSpacerItem(hp.make_h_spacer() if orientation == Qt.Orientation.Horizontal else hp.make_v_spacer())
        self.layout_.setSpacing(0)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.max_size = 28

    @property
    def max_size(self) -> int:
        """Return maximum size."""
        return self.maximumHeight() if self.orientation == Qt.Orientation.Horizontal else self.maximumWidth()

    @max_size.setter
    def max_size(self, value: int):
        self.setMaximumHeight(value) if self.orientation == Qt.Orientation.Horizontal else self.setMaximumWidth(value)

    @property
    def n_items(self) -> int:
        """Return the number of items in the layout."""
        return self.layout_.count()

    def _make_qta_button(
        self,
        name: str,
        func: ty.Optional[ty.Callable] = None,
        tooltip: ty.Optional[str] = None,
        checkable: bool = False,
        check: bool = False,
        size: ty.Tuple[int, int] = (26, 26),
        flat: bool = True,
        small: bool = False,
        average: bool = False,
    ):
        if small or average:
            size = None
        btn = hp.make_qta_btn(
            self,
            name,
            tooltip=tooltip,
            flat=flat,
            medium=False,
            size=size,
            checkable=checkable,
            checked=check,
            func=func,
            small=small,
            average=average,
            properties={"wide_border": True},
        )
        self._tools[name] = btn
        return btn

    def add_button(self, button):
        """Add any button the toolbar."""
        self.layout_.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        return button

    def add_widget(self, widget):
        """Insert any widget at specified position."""
        self.layout_.addWidget(widget, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    def add_layout(self, layout):
        """Insert any layout at specified position."""
        self.layout_.addWidget(layout)
        return layout

    def add_qta_tool(
        self,
        name: str,
        flat: bool = True,
        func: ty.Optional[ty.Callable] = None,
        tooltip: ty.Optional[str] = None,
        checkable: bool = False,
        check: bool = False,
        size: ty.Tuple[int, int] = (26, 26),
        small: bool = False,
        average: bool = False,
    ):
        """Insert tool."""
        btn = self._make_qta_button(
            name,
            func=func,
            tooltip=tooltip,
            checkable=checkable,
            check=check,
            size=size,
            flat=flat,
            small=small,
            average=average,
        )
        self.add_button(btn)
        return btn

    def insert_button(self, button, index: int = 0, set_size: bool = True):
        """Insert any button at specified position."""
        if hasattr(button, "set_size") and set_size:
            button.set_size((26, 26))
        self.layout_.insertWidget(index, button, alignment=Qt.AlignmentFlag.AlignCenter)
        return button

    def insert_widget(self, widget, index: int = 0):
        """Insert any widget at specified position."""
        self.layout_.insertWidget(index, widget, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    def insert_layout(self, layout, index: int = 0):
        """Insert any layout at specified position."""
        self.layout_.insertLayout(index, layout)
        return layout

    def insert_qta_tool(
        self,
        name: str,
        flat: bool = False,
        func: ty.Optional[ty.Callable] = None,
        tooltip: ty.Optional[str] = None,
        checkable: bool = False,
        check: bool = False,
        size: ty.Tuple[int, int] = (26, 26),
        hidden: bool = False,
    ):
        """Insert tool."""
        btn = self._make_qta_button(
            name, flat=flat, func=func, tooltip=tooltip, checkable=checkable, check=check, size=size
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
        spacer = hp.make_spacer_widget()  # make_v_spacer() if self.orientation == Qt.Orientation.Horizontal else make_h_spacer()
        self.layout_.insertWidget(0, spacer, stretch=True)

    def append_spacer(self) -> None:
        """Insert spacer item."""
        spacer = hp.make_spacer_widget()  # make_v_spacer() if self.orientation == Qt.Orientation.Horizontal else make_h_spacer()
        self.layout_.insertWidget(self.layout_.count(), spacer, stretch=True)

    def show_border(self):
        """Show border."""
        self.setFrameShape(QFrame.Box)

    def swap_orientation(self):
        """Swap orientation."""
        self.orientation = (
            QHBoxLayout.Direction.LeftToRight
            if self.orientation == Qt.Orientation.Vertical
            else QVBoxLayout.Direction.TopToBottom
        )
        self.layout_.setDirection(self.orientation)
        self.layout_.invalidate()
        self.layout_.update()


if __name__ == "__main__":
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
