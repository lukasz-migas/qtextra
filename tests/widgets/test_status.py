"""Tests for status bar widgets."""

import builtins
import sys
import types

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon, QMovie
from qtpy.QtWidgets import QMainWindow, QMenu

from qtextra.widgets.qt_status import (
    QtStatusbarCPU,
    QtStatusbarIconWidget,
    QtStatusbarLabel,
    QtStatusbarMemory,
    QtStatusbarProcessMemory,
    QtStatusbarProgressbar,
    QtStatusbarSpinner,
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


def test_status_bar_spinner_start_stop(status_bar, qtbot):
    win, statusbar = status_bar()
    spinner = QtStatusbarSpinner(win, statusbar)

    spinner.start()
    assert spinner.spinner.isHidden() is False
    assert spinner.movie.state() == QMovie.MovieState.Running

    spinner.stop()
    assert spinner.spinner.isHidden() is True
    assert spinner.movie.state() == QMovie.MovieState.NotRunning


def test_status_bar_icon_widget_signal(status_bar, qtbot):
    win, statusbar = status_bar()
    widget = QtStatusbarIconWidget(win, statusbar, name="mdi.information-outline")

    with qtbot.waitSignal(widget.evt_clicked, timeout=1000):
        qtbot.mouseRelease(widget, Qt.LeftButton)


def test_status_bar_cpu_is_supported_handles_missing_psutil(monkeypatch, status_bar):
    win, statusbar = status_bar()
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psutil":
            raise ImportError("psutil unavailable")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    widget = QtStatusbarCPU(win, statusbar)

    assert widget.is_supported() is False
    assert widget.isHidden() is True


def test_status_bar_memory_get_value_format(monkeypatch, status_bar):
    win, statusbar = status_bar()
    widget = QtStatusbarMemory(win, statusbar)

    monkeypatch.setattr("qtextra.utils.utilities.memory_usage", lambda: 7)

    assert widget.get_value() == "Mem   7%"


def test_status_bar_process_memory_get_value_format(monkeypatch, status_bar):
    win, statusbar = status_bar()
    widget = QtStatusbarProcessMemory(win, statusbar)

    monkeypatch.setattr("qtextra.utils.utilities.process_memory_usage", lambda: 12)

    assert widget.get_value() == "Mem  12%"


def test_status_bar_cpu_get_value_format(monkeypatch, status_bar):
    win, statusbar = status_bar()
    widget = QtStatusbarCPU(win, statusbar)

    monkeypatch.setitem(sys.modules, "psutil", types.SimpleNamespace(cpu_percent=lambda interval=0: 3))

    assert widget.get_value() == "CPU   3%"
