"""Docked widget.

This module is heavily inspired by napari's implementation which minimised size of the title bar while making it quite
visually appealing.
"""

from functools import reduce
from operator import ior
from typing import List, Optional

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDockWidget, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from qtextra.config.events import EVENTS
from qtextra.helpers import qt_signals_blocked


class QtDockedWidget(QDockWidget):
    """Wrap a QWidget in a QDockWidget and forward viewer events.

    Parameters
    ----------
    widget : QWidget
        `widget` that will be added as QDockWidget's main widget.
    name : str
        Name of dock widget.
    area : str
        Side of the main window to which the new dock widget will be added.
        Must be in {'left', 'right', 'top', 'bottom'}
    allowed_areas : list[str], optional
        Areas, relative to main window, that the widget is allowed dock.
        Each item in list must be in {'left', 'right', 'top', 'bottom'}
        By default, all areas are allowed.
    """

    def __init__(
        self,
        parent,
        widget: QWidget,
        *,
        name: str = "",
        area: str = "bottom",
        allowed_areas: Optional[List[str]] = None,
    ):
        self._parent = parent
        super().__init__(name)
        self.name = name

        areas = {
            "left": Qt.DockWidgetArea.LeftDockWidgetArea,
            "right": Qt.DockWidgetArea.RightDockWidgetArea,
            "top": Qt.DockWidgetArea.TopDockWidgetArea,
            "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
        }
        if area not in areas:
            raise ValueError(f"area argument must be in {list(areas.keys())}")
        self.area = area
        self.qt_area = areas[area]

        if allowed_areas:
            if not isinstance(allowed_areas, (list, tuple)):
                raise TypeError("`allowed_areas` must be a list or tuple")
            if not all(area in areas for area in allowed_areas):
                raise ValueError(f"all allowed_areas argument must be in {list(areas.keys())}")
            allowed_areas = reduce(ior, [areas[a] for a in allowed_areas])
        else:
            allowed_areas = Qt.AllDockWidgetAreas
        self.setAllowedAreas(allowed_areas)
        self.setMinimumHeight(50)
        self.setMinimumWidth(50)
        self.setObjectName(name)

        self.setWidget(widget)
        if widget:
            widget.setParent(self)
        self._initial_features = self.features()
        self.dockLocationChanged.connect(self._set_title_orientation)

        # custom title bar
        self.title = QtCustomTitleBar(self, title=self.name)
        self.setTitleBarWidget(self.title)
        self.visibilityChanged.connect(self._on_visibility_changed)
        EVENTS.evt_splash_msg.emit(f"Setup {name} panel...")

    def keyPressEvent(self, event):  # noqa
        # if you subclass QtViewerDockWidget and override the keyPressEvent
        # method, be sure to call super().keyPressEvent(event) at the end of
        # your method to pass uncaught key-combinations to the viewer.
        return self._parent.keyPressEvent(event)

    def _set_title_orientation(self, area):
        if area in (Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea):
            features = self._initial_features
        else:
            features = self._initial_features | self.DockWidgetVerticalTitleBar
        self.setFeatures(features)

    @property
    def is_vertical(self):
        """Checks where dock is in vertical position."""
        if not self.isFloating():
            par = self._parent
            if par and hasattr(par, "dockWidgetArea"):
                return par.dockWidgetArea(self) in (
                    Qt.LeftDockWidgetArea,
                    Qt.RightDockWidgetArea,
                )
        return self.size().height() > self.size().width()

    def _on_visibility_changed(self, visible):
        if not visible:
            return
        with qt_signals_blocked(self):
            self.setTitleBarWidget(None)
            if not self.isFloating():
                self.title = QtCustomTitleBar(self, title=self.name, vertical=not self.is_vertical)
                self.setTitleBarWidget(self.title)


class QtCustomTitleBar(QLabel):
    """A widget to be used as the titleBar in the QtViewerDockWidget.

    Keeps vertical size minimal, has a hand cursor and styles (in stylesheet)
    for hover. Close and float buttons.

    Parameters
    ----------
    parent : QDockWidget
        The QtViewerDockWidget to which this titlebar belongs
    title : str
        A string to put in the titlebar.
    vertical : bool
        Whether this titlebar is oriented vertically or not.
    """

    def __init__(self, parent, title: str = "", vertical=False):
        super().__init__(parent)
        self.setObjectName("QtCustomTitleBar")
        self.setProperty("vertical", str(vertical))
        self.vertical = vertical
        self.setToolTip("Drag to move or double-click to float")

        line = QFrame(self)
        line.setObjectName("QtCustomTitleBarLine")

        self.close_button = QPushButton(self)
        self.close_button.setToolTip("Hide this panel")
        self.close_button.setObjectName("QtTitleBarCloseButton")
        self.close_button.setCursor(Qt.ArrowCursor)
        self.close_button.clicked.connect(lambda: self.parent().toggleViewAction().trigger())
        self.float_button = QPushButton(self)
        self.float_button.setToolTip("Float this panel")
        self.float_button.setObjectName("QtTitleBarFloatButton")
        self.float_button.setCursor(Qt.ArrowCursor)
        self.float_button.clicked.connect(lambda: self.parent().setFloating(not self.parent().isFloating()))
        self.title = QLabel(title, self)
        self.title.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum))

        if vertical:
            layout = QVBoxLayout()
            layout.setSpacing(4)
            layout.setContentsMargins(0, 8, 0, 8)
            line.setFixedWidth(1)
            layout.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(self.float_button, 0, Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(line, 0, Qt.AlignmentFlag.AlignHCenter)
            self.title.hide()

        else:
            layout = QHBoxLayout()
            layout.setSpacing(4)
            layout.setContentsMargins(8, 1, 8, 0)
            line.setFixedHeight(1)
            layout.addWidget(self.close_button)
            layout.addWidget(self.float_button)
            layout.addWidget(line)
            layout.addWidget(self.title)

        self.setLayout(layout)
        self.setCursor(Qt.OpenHandCursor)

    def sizeHint(self):
        """Set size of the title."""
        # this seems to be the correct way to set the height of the titlebar
        szh = super().sizeHint()
        if self.vertical:
            szh.setWidth(20)
        else:
            szh.setHeight(20)
        return szh
