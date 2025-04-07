"""Slightly modified QToolButton with nicer interface."""

from typing import Callable, List, Optional, Tuple, Union

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QCursor, QIcon
from qtpy.QtWidgets import QMenu, QToolButton


class QtToolButton(QToolButton):
    """QToolButton."""

    _icon, _pixmap = None, None

    def __init__(self, parent, text="", icon: Union[QIcon, None] = None):
        super().__init__(parent)
        self.setText(text)
        self.setPopupMode(self.ToolButtonPopupMode.MenuButtonPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # Widget setup
        self._icon_size = QSize(16, 16)
        if icon:
            self.set_icon(icon)

    def set_menu(self, menu: QMenu, action: Optional[Callable] = None, auto_pop: bool = True) -> None:
        """Set tool button menu."""
        if not isinstance(menu, QMenu):
            raise ValueError("'menu' argument must be a QMenu instance")

        self.setMenu(menu)
        if action:
            if not callable(action):
                raise ValueError("'action' argument must be a callable")
            menu.triggered.connect(action)
        if auto_pop:
            self.pressed.connect(self.autopop)

    def set_icon(self, icon: Union[QIcon, None]) -> None:
        """Set the icon for the status bar widget."""
        if icon is not None and isinstance(icon, QIcon):
            self._icon = icon
            self._pixmap = icon.pixmap(self._icon_size)
            self.setIcon(icon)
            self.setMinimumWidth(37)  # based on an icon of size (16, 16)

    def set_size(self, size: Union[List, Tuple]) -> None:
        """Set size of the button."""
        if isinstance(size, (list, tuple)):
            self.setMinimumSize(QSize(*size))
            self.setMaximumSize(QSize(*size))

    def autopop(self) -> None:
        """When button is clicked (not necessarily on the down arrow, menu will be shown."""
        self.menu().popup(QCursor.pos())

    def popup(self) -> None:
        """When button is clicked (not necessarily on the down arrow, menu will be shown."""
        self.menu().popup(QCursor.pos())


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe()

        menu = QMenu(None)
        menu.addAction("Action 1")

        btn1 = QtToolButton(frame, text="None")
        btn1.set_menu(menu, print)

        ha.addWidget(btn1)
        frame.show()
        sys.exit(app.exec_())

    _main()  # type: ignore[no-untyped-call]
