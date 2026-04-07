"""Tests for the icon multi-select widgets."""

from __future__ import annotations

from qtpy.QtCore import QSize

import qtextra.helpers as hp
from qtextra.widgets.qt_select_multi import IconSelectionWidget, QtMultiIconSelect


def test_qt_multi_icon_select_formats_tooltips_and_applies_size(qtbot) -> None:
    widget = QtMultiIconSelect(None, icon_size=(30, 30))
    qtbot.addWidget(widget)

    widget.set_options([("help", "Help"), ("warning", "Warning")], ["warning"])

    assert widget.text_edit.text() == "Warning"

    popup = IconSelectionWidget(widget, icon_size=(30, 30))
    qtbot.addWidget(popup)
    popup.set_options([("help", "Help"), ("warning", "Warning")], ["warning"])

    assert popup.buttons["help"].iconSize() == QSize(30, 30)
    assert popup.buttons["warning"].toolTip() == "Warning"


def test_icon_selection_widget_single_select_updates_and_closes(qtbot, monkeypatch) -> None:
    widget = IconSelectionWidget(None, allow_multiple=False)
    qtbot.addWidget(widget)
    widget.set_options([("help", "Help"), ("warning", "Warning")], ["help"])

    updates: list[list[str]] = []
    accepted: list[bool] = []
    widget.evt_update.connect(updates.append)

    def _accept(_self) -> None:
        accepted.append(True)

    monkeypatch.setattr("qtextra.widgets.qt_select_multi.QtFramelessPopup.accept", _accept)

    widget.buttons["warning"].click()

    assert widget.selected_options == ["warning"]
    assert updates == [["warning"]]
    assert accepted == [True]


def test_icon_selection_widget_multi_select_allows_multiple_checked_buttons(qtbot) -> None:
    widget = IconSelectionWidget(None, allow_multiple=True)
    qtbot.addWidget(widget)
    widget.set_options([("help", "Help"), ("warning", "Warning"), ("info", "Info")], ["help"])

    temporary_updates: list[list[str]] = []
    widget.evt_temp_changed.connect(temporary_updates.append)

    widget.buttons["warning"].click()
    widget.buttons["info"].click()

    assert widget.buttons["help"].isCheckable() is True
    assert set(widget.selected_options) == {"help", "warning", "info"}
    assert temporary_updates[-1] == ["help", "warning", "info"]


def test_make_multi_icon_select_initializes_widget(qtbot) -> None:
    widget = hp.make_multi_icon_select(
        None,
        description="Icon help",
        options=[("help", "Help"), ("warning", "Warning")],
        value=["warning"],
        allow_multiple=True,
        icon_size=(26, 26),
    )
    qtbot.addWidget(widget)

    assert isinstance(widget, QtMultiIconSelect)
    assert widget.toolTip() == "Icon help"
    assert widget.selected_options == ["warning"]
    assert widget.icon_size == (26, 26)


def test_choose_from_icon_list_returns_selected_value(monkeypatch) -> None:
    selected = ["warning"]

    def _set_window_flags(self, *_args) -> None:
        return None

    def _set_options(self, _options, _selected) -> None:
        return None

    def _exec(self) -> int:
        self.selection = selected
        return 1

    monkeypatch.setattr("qtextra.widgets.qt_select_multi.IconSelectionWidget.setWindowFlags", _set_window_flags)
    monkeypatch.setattr("qtextra.widgets.qt_select_multi.IconSelectionWidget.set_options", _set_options)
    monkeypatch.setattr("qtextra.widgets.qt_select_multi.IconSelectionWidget.exec", _exec)
    result = hp.choose_from_icon_list(None, [("help", "Help"), ("warning", "Warning")], multiple=False)

    assert result == "warning"
