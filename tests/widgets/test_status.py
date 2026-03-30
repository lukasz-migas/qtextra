"""Tests for status bar widgets."""

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QMainWindow, QMenu

from qtextra.widgets.qt_status import (
    QtStatusbarCPU,
    QtStatusbarLabel,
    QtStatusbarMemory,
    QtStatusbarProgressbar,
    QtStatusbarToolBtn,
    QtStatusbarWidget,
)


@pytest.fixture
def make_menu(qapp):
    """Make menu."""

    def _wrap():
        menu = QMenu(None)
        menu.addAction("Action 1")
        return menu

    return _wrap


@pytest.fixture
def status_bar(qtbot):
    """Set up StatusBarWidget."""

    def _wrap():
        win = QMainWindow()
        win.setWindowTitle("Status widgets test")
        win.resize(900, 300)
        statusbar = win.statusBar()
        qtbot.addWidget(win)
        return win, statusbar

    return _wrap


def test_status_bar_widgets(status_bar, qtbot):
    win, statusbar = status_bar()
    swidgets = []
    for klass in (QtStatusbarMemory, QtStatusbarCPU, QtStatusbarLabel, QtStatusbarToolBtn, QtStatusbarProgressbar):
        swidget = klass(win, statusbar)
        swidgets.append(swidget)
    assert win
    assert len(swidgets) == 5


def test_status_bar_tool_btn(status_bar, make_menu, get_icon_path, qtbot):
    win, statusbar = status_bar()
    menu = make_menu()
    widget = QtStatusbarToolBtn(win, statusbar)

    widget.set_size((10, 10))
    size = widget.size()
    assert size.width() <= 10 and size.height() <= 10

    with pytest.raises(ValueError) as __:
        widget.set_menu(menu, "FAIL")

    widget.set_menu(menu, print)
    assert widget.menu() == menu

    # check icon
    icon = None
    widget.set_icon(icon)
    assert widget.icon().isNull() is True

    # will check if the path was not returned as None
    if get_icon_path:
        icon = QIcon(get_icon_path)
        widget.set_icon(icon)
        assert widget.icon().availableSizes()[0] == icon.availableSizes()[0]


class StatusBarWidgetTest(QtStatusbarWidget):
    def get_tooltip(self):
        return "tooltip"

    def get_icon(self):
        return "icon"


def test_status_bar_widget_signal(status_bar, qtbot):
    win, statusbar = status_bar()
    w = StatusBarWidgetTest(win, statusbar)

    with qtbot.waitSignal(w.evt_clicked, timeout=1000):
        qtbot.mouseRelease(w, Qt.LeftButton)

    assert w.get_tooltip() == "tooltip"
    assert w.get_icon() == "icon"
