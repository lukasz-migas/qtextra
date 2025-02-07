import pytest
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QMenu

from qtextra.widgets.qt_button_tool import QtToolButton


@pytest.fixture
def make_menu(qapp):
    """Make menu."""

    def _wrap():
        menu = QMenu(None)
        menu.addAction("Action 1")
        return menu

    return _wrap


@pytest.fixture
def setup_widget(qtbot):
    """Set up error report dialog."""

    def _wrap():
        widget = QtToolButton(None, "test")
        qtbot.addWidget(widget)
        return widget

    return _wrap


def test_qt_tool_button(setup_widget, make_menu, get_icon_path, qtbot):
    widget = setup_widget()
    menu = make_menu()

    # check label
    assert widget.text() == "test"

    # check menu
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

    widget.set_size((10, 10))
    size = widget.size()
    assert size.width() <= 10 and size.height() <= 10


def test_qt_tool_button_wrong(setup_widget, make_menu, get_icon_path, qtbot):
    widget = setup_widget()
    menu = make_menu()

    with pytest.raises(ValueError) as __:
        widget.set_menu(menu, "not a callable")

    with pytest.raises(ValueError) as __:
        widget.set_menu("not a menu", print)
