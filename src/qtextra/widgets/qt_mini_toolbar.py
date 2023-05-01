"""Mini toolbar."""
import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp


class QtMiniToolbar(QWidget):
    """Mini toolbar."""

    def __init__(
        self, parent, orientation: Qt.Orientation = Qt.Horizontal, on_color: str = "#ebffeb", add_spacer: bool = True
    ):
        super().__init__(parent)
        self._tools = {}
        self.orientation = orientation
        self.on_color = on_color

        self.layout = QHBoxLayout(self) if orientation == Qt.Horizontal else QVBoxLayout(self)
        if add_spacer:
            self.layout.addSpacerItem(hp.make_h_spacer() if orientation == Qt.Horizontal else hp.make_v_spacer())
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.max_size = 28

    @property
    def max_size(self) -> int:
        """Return maximum size."""
        return self.maximumHeight() if self.orientation == Qt.Horizontal else self.maximumWidth()

    @max_size.setter
    def max_size(self, value: int):
        self.setMaximumHeight(value) if self.orientation == Qt.Horizontal else self.setMaximumWidth(value)

    @property
    def n_items(self) -> int:
        """Return the number of items in the layout."""
        return self.layout.count()

    def _make_qta_button(
        self,
        name: str,
        flat: bool = True,
        func: ty.Optional[ty.Callable] = None,
        tooltip: str = None,
        checkable: bool = False,
        check: bool = False,
        size: ty.Tuple[int, int] = (26, 26),
    ):
        btn = hp.make_qta_btn(self, name, tooltip=tooltip, flat=flat, medium=False, size=size, checkable=checkable)
        if callable(func):
            if checkable:
                btn.toggled.connect(func)
            else:
                btn.clicked.connect(func)
        if check:
            btn.setChecked(True)
        self._tools[name] = btn
        return btn

    def add_button(self, button):
        """Add any button the toolbar."""
        self.layout.addWidget(button, alignment=Qt.AlignCenter)
        return button

    def add_widget(self, widget):
        """Insert any widget at specified position."""
        self.layout.addWidget(widget, alignment=Qt.AlignCenter)
        return widget

    def add_layout(self, layout):
        """Insert any layout at specified position."""
        self.layout.addWidget(layout)
        return layout

    def add_qta_tool(
        self,
        name: str,
        flat: bool = True,
        func: ty.Optional[ty.Callable] = None,
        tooltip: str = None,
        checkable: bool = False,
        check: bool = False,
        size: ty.Tuple[int, int] = (26, 26),
    ):
        """Insert tool."""
        btn = self._make_qta_button(name, flat, func, tooltip, checkable, check, size=size)
        self.add_button(btn)
        return btn

    def insert_button(self, button, index: int = 0):
        """Insert any button at specified position."""
        if hasattr(button, "set_size"):
            button.set_size((26, 26))
        self.layout.insertWidget(index, button, alignment=Qt.AlignCenter)
        return button

    def insert_widget(self, widget, index: int = 0):
        """Insert any widget at specified position."""
        self.layout.insertWidget(index, widget, alignment=Qt.AlignCenter)
        return widget

    def insert_layout(self, layout, index: int = 0):
        """Insert any layout at specified position."""
        self.layout.insertLayout(index, layout)
        return layout

    def insert_qta_tool(
        self,
        name: str,
        flat: bool = True,
        func: ty.Optional[ty.Callable] = None,
        tooltip: str = None,
        checkable: bool = False,
        check: bool = False,
        size: ty.Tuple[int, int] = (26, 26),
    ):
        """Insert tool."""
        btn = self._make_qta_button(name, flat, func, tooltip, checkable, check, size=size)
        self.insert_button(btn)
        return btn

    def insert_separator(self):
        """Insert horizontal or vertical separator."""
        sep = hp.make_v_line() if self.orientation == Qt.Horizontal else hp.make_h_line(self)
        self.layout.insertWidget(0, sep)

    def insert_spacer(self):
        """Insert spacer item."""
        spacer = hp.make_spacer_widget()  # make_v_spacer() if self.orientation == Qt.Horizontal else make_h_spacer()
        self.layout.insertWidget(0, spacer, stretch=True)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra._dev_tools import qframe

    app, frame, ha = qframe()
    h = QtMiniToolbar(None, orientation=Qt.Horizontal)
    h.add_qta_tool("fa5.file", tooltip="File")
    h.add_qta_tool("fa5.file", tooltip="File")
    h.add_qta_tool("fa5.file", tooltip="File")
    ha.addWidget(h)

    h = QtMiniToolbar(None, orientation=Qt.Vertical)
    h.add_qta_tool("fa5.file", tooltip="File")
    h.add_qta_tool("fa5.file", tooltip="File")
    h.add_qta_tool("fa5.file", tooltip="File")
    ha.addWidget(h)
    frame.show()
    sys.exit(app.exec_())
