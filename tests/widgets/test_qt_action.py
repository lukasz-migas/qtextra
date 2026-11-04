"""Tests for QtAwesome action icons."""

from typing import Any

from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QMenu, QMenuBar, QWidget

from qtextra import helpers as hp
from qtextra.config import THEMES
from qtextra.widgets import qt_action


def test_native_menu_icons_follow_menu_context(qtbot: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(qt_action, "platform", "darwin")
    monkeypatch.setattr(QMenuBar, "isNativeMenuBar", lambda self: True)
    parent = QWidget()
    qtbot.addWidget(parent)
    menubar = QMenuBar(parent)
    menubar.setNativeMenuBar(True)
    menu = hp.make_menu(parent, "Menu")
    submenu = hp.make_menu(parent, "Submenu", menu=menu)
    other_submenu = QMenu("Other submenu", parent)
    submenu.addMenu(other_submenu)
    menu_action = hp.make_menu_item(parent, "Menu action", icon="save", menu=menu)
    submenu_action = hp.make_menu_item(parent, "Submenu action", icon="save", menu=submenu)
    other_action = hp.make_menu_item(parent, "Other action", icon="save", menu=other_submenu)
    popup = hp.make_menu(parent, "Popup")
    popup_action = hp.make_menu_item(parent, "Popup action", icon="save", menu=popup)
    widget_action = hp.make_action(parent, "save", "Widget action")

    # The menus are populated before attaching them to the menu bar.
    menubar.addAction(menu.menuAction())
    menu.aboutToShow.emit()
    assert other_action.icon().isMask()
    submenu.aboutToShow.emit()
    popup.aboutToShow.emit()
    assert menu_action.icon().isMask()
    assert submenu_action.icon().isMask()
    assert not popup_action.icon().isMask()
    assert not widget_action.icon().isMask()

    # Moving a menu back to an ordinary popup restores application styling.
    menubar.removeAction(menu.menuAction())
    menu.aboutToShow.emit()
    submenu.aboutToShow.emit()
    assert not menu_action.icon().isMask()
    assert not submenu_action.icon().isMask()
    assert not other_action.icon().isMask()


def test_non_native_menu_icons_use_application_theme(qtbot: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(qt_action, "platform", "darwin")
    parent = QWidget()
    qtbot.addWidget(parent)
    menubar = QMenuBar(parent)
    menubar.setNativeMenuBar(False)
    menu = hp.make_menu(parent, "Menu")
    action = hp.make_menu_item(parent, "Action", icon="save", menu=menu)
    menubar.addAction(menu.menuAction())
    menu.aboutToShow.emit()
    assert not action.icon().isMask()


def test_action_retains_icon_options_and_menu_state_on_theme_change(qtbot: Any, monkeypatch: Any) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    calls: list[tuple[str, dict[str, Any]]] = []
    original_icon = qt_action.qtawesome.icon

    def record_icon(name: str, **kwargs: Any) -> QIcon:
        calls.append((name, kwargs.copy()))
        return original_icon(name, **kwargs)

    monkeypatch.setattr(qt_action.qtawesome, "icon", record_icon)
    action = qt_action.QtQtaAction(parent)
    action.set_qta("save", scale_factor=0.7, color="#123456")
    assert calls[-1][1]["color"] == "#123456"
    action._set_native_menu(True)
    assert calls[-1][1] == {"scale_factor": 0.7, "color": "black"}
    assert not original_icon(calls[-1][0], **calls[-1][1]).isMask()
    THEMES.evt_theme_icon_changed.emit()
    assert action.icon().isMask()
    assert calls[-1][1] == {"scale_factor": 0.7, "color": "black"}
    action._set_native_menu(False)
    assert calls[-1][1] == {"scale_factor": 0.7, "color": "#123456"}


def test_app_theme_changes_refresh_normal_action(qtbot: Any, monkeypatch: Any) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    colors: list[str] = []
    original_icon = qt_action.qtawesome.icon
    current_color = ["#111111"]

    def record_icon(name: str, **kwargs: Any) -> QIcon:
        colors.append(kwargs["color"])
        return original_icon(name, **kwargs)

    monkeypatch.setattr(qt_action.qtawesome, "icon", record_icon)
    monkeypatch.setattr(THEMES, "get_hex_color", lambda name: current_color[0])
    action = qt_action.QtQtaAction(parent)
    action.set_qta("save")
    assert colors[-1] == "#111111"
    current_color[0] = "#eeeeee"
    THEMES.evt_theme_icon_changed.emit()
    assert colors[-1] == "#eeeeee"
    assert not action.icon().isMask()
