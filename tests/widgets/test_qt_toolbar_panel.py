import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QWidget

from qtextra.widgets.qt_button_icon import QtLabelledToolbarPushButton
from qtextra.widgets.qt_toolbar_panel import QtPanelToolbar


def _make_overflow_toolbar(qtbot, *, height=180, auto_hide=True):
    window = QMainWindow()
    window.resize(320, height)
    qtbot.addWidget(window)

    toolbar = QtPanelToolbar(window, label_hidden=False, auto_hide=auto_hide)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    top_buttons = [
        toolbar.add_widget(name, title=title)
        for name, title in [
            ("home", "Home"),
            ("zoom", "Search"),
            ("gear", "Settings"),
            ("help", "Help"),
            ("info", "Extensions"),
        ]
    ]
    bottom_buttons = [
        toolbar.add_widget("bug", location="bottom"),
        toolbar.add_widget("save", location="bottom"),
    ]
    window.show()
    return window, toolbar, top_buttons, bottom_buttons


def test_qt_labelled_toolbar_push_button_constrains_label_width(qtbot):
    widget = QtLabelledToolbarPushButton()
    qtbot.addWidget(widget)

    widget.set_qta_size_preset("large")
    widget.set_label("Very long toolbar label that should not widen the whole toolbar")
    icon_width = widget.image_btn.sizeHint().width()

    assert widget.label.wordWrap() is False
    assert widget.label.width() <= icon_width
    assert widget.label.height() <= widget.label.fontMetrics().lineSpacing() + 1
    assert widget.sizeHint().width() <= icon_width


def test_qt_panel_toolbar_label_hidden_propagates_to_labelled_buttons(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    button = toolbar.add_widget("gear", title="Very long toolbar label")
    icon_width = button.image_btn.sizeHint().width()

    assert isinstance(button, QtLabelledToolbarPushButton)
    assert button.label_hidden is False
    assert button.sizeHint().width() <= icon_width

    toolbar.label_hidden = True

    assert button.label_hidden is True


def test_qt_labelled_toolbar_push_button_preserves_explicit_multiline_labels(qtbot):
    widget = QtLabelledToolbarPushButton()
    qtbot.addWidget(widget)

    widget.set_qta_size_preset("large")
    widget.set_label("First line\nSecond line")

    assert widget.label.text().count("\n") == 1
    assert widget.label.height() > widget.label.fontMetrics().lineSpacing()


def test_qt_labelled_toolbar_push_button_can_disable_elision(qtbot):
    widget = QtLabelledToolbarPushButton(elide=False)
    qtbot.addWidget(widget)

    widget.set_qta_size_preset("large")
    widget.set_label("Very long label")

    assert widget.elide is False
    assert "..." not in widget.label.text()
    assert widget.label.width() > widget.image_btn.sizeHint().width()


def test_qt_panel_toolbar_add_widget_passes_elide_flag(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    button = toolbar.add_widget("gear", title="Very long label", elide=False)

    assert isinstance(button, QtLabelledToolbarPushButton)
    assert button.elide is False
    assert button.label.width() > button.image_btn.sizeHint().width()


def test_qt_panel_toolbar_centers_buttons_when_non_elided_label_expands_width(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    plain_button = toolbar.add_widget("home")
    wide_button = toolbar.add_widget("gear", title="Very long label", elide=False)

    assert plain_button.width() == wide_button.width()


def test_qt_panel_toolbar_rejects_duplicate_button_names(qtbot):
    toolbar = QtPanelToolbar()
    qtbot.addWidget(toolbar)

    toolbar.add_widget("home")

    with pytest.raises(ValueError, match="already exists"):
        toolbar.add_widget("home")


def test_qt_panel_toolbar_disabling_active_button_switches_to_another_panel(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    home_panel = QWidget()
    settings_panel = QWidget()

    home_button = toolbar.add_widget("home", widget=home_panel)
    settings_button = toolbar.add_widget("gear", widget=settings_panel)
    settings_button.click()

    toolbar.disable_widget(settings_button)

    assert toolbar.stack_widget.currentWidget() is home_panel
    assert settings_button.isChecked() is False
    assert home_button.isChecked() is True


def test_qt_panel_toolbar_hiding_wide_button_reduces_shared_width(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    plain_button = toolbar.add_widget("home")
    wide_button = toolbar.add_widget("gear", title="Very long label", elide=False)
    expanded_width = plain_button.width()

    toolbar.disable_widget(wide_button)

    assert plain_button.width() < expanded_width


def test_qt_panel_toolbar_collapses_trailing_top_buttons_into_menu(qtbot):
    window, toolbar, top_buttons, bottom_buttons = _make_overflow_toolbar(qtbot, height=240)
    panel = toolbar._widget

    qtbot.waitUntil(lambda: bool(panel._overflow_hidden))

    visible_top = [button for button in top_buttons if button not in panel._overflow_hidden]
    hidden_top = [button for button in top_buttons if button in panel._overflow_hidden]
    assert top_buttons == visible_top + hidden_top
    assert all(panel._button_dict[button].isVisible() for button in bottom_buttons)
    assert all(button.isVisible() for button in bottom_buttons)
    assert panel._overflow_action.isVisible()
    assert all(
        panel._buttons.actions().index(panel._button_dict[button])
        < panel._buttons.actions().index(panel._overflow_action)
        for button in top_buttons
    )
    assert panel._buttons.actions().index(panel._overflow_action) < panel._buttons.actions().index(panel._spacer)
    last_visible_geometry = panel._buttons.actionGeometry(panel._button_dict[visible_top[-1]])
    overflow_geometry = panel._buttons.actionGeometry(panel._overflow_action)
    button_gap = overflow_geometry.top() - last_visible_geometry.bottom()
    assert 0 < button_gap <= panel._buttons.layout().spacing() + 1

    visible_menu_actions = [action for action in panel._overflow_menu.actions() if action.isVisible()]
    assert [action.text() for action in visible_menu_actions] == [
        panel._overflow_labels[button] for button in hidden_top
    ]
    assert all(not action.icon().isNull() for action in visible_menu_actions)

    window.resize(320, 600)
    qtbot.waitUntil(lambda: not panel._overflow_hidden)
    assert all(panel._button_dict[button].isVisible() for button in top_buttons)
    assert not panel._overflow_action.isVisible()


def test_qt_panel_toolbar_overflow_action_invokes_original_callback(qtbot):
    window, toolbar, _, _ = _make_overflow_toolbar(qtbot)
    panel = toolbar._widget
    calls = []
    callback_button = toolbar.add_widget("reload", title="Reload", func=lambda: calls.append("reload"))

    qtbot.waitUntil(lambda: callback_button in panel._overflow_hidden)
    panel._overflow_menu_actions[callback_button].trigger()

    assert calls == ["reload"]
    window.close()


def test_qt_panel_toolbar_keeps_active_overflowed_panel_selected(qtbot):
    window = QMainWindow()
    window.resize(320, 600)
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=False)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)

    panels = [QWidget() for _ in range(5)]
    buttons = [
        toolbar.add_widget(name, title=title, widget=widget)
        for name, title, widget in zip(
            ["home", "zoom", "gear", "help", "info"],
            ["Home", "Search", "Settings", "Help", "Extensions"],
            panels,
            strict=True,
        )
    ]
    toolbar.add_widget("bug", location="bottom")
    window.show()
    qtbot.mouseClick(buttons[-1].image_btn, Qt.MouseButton.LeftButton)
    assert toolbar.stack_widget.currentWidget() is panels[-1]

    window.resize(320, 180)
    panel = toolbar._widget
    qtbot.waitUntil(lambda: buttons[-1] in panel._overflow_hidden)
    panel._sync_overflow_menu()

    assert toolbar.stack_widget.currentWidget() is panels[-1]
    assert buttons[-1].isChecked()
    assert panel._overflow_menu_actions[buttons[-1]].isChecked()


def test_qt_panel_toolbar_overflow_menu_action_activates_panel(qtbot):
    window = QMainWindow()
    window.resize(320, 180)
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=False)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)

    home_panel = QWidget()
    settings_panel = QWidget()
    toolbar.add_widget("home", title="Home", widget=home_panel)
    toolbar.add_widget("zoom", title="Search")
    settings_button = toolbar.add_widget("gear", title="Settings", widget=settings_panel)
    toolbar.add_widget("help", title="Help")
    toolbar.add_widget("bug", location="bottom")
    window.show()

    panel = toolbar._widget
    qtbot.waitUntil(lambda: settings_button in panel._overflow_hidden)
    panel._overflow_menu_actions[settings_button].trigger()

    assert toolbar.stack_widget.currentWidget() is settings_panel
    assert settings_button.isChecked()


def test_qt_panel_toolbar_manual_hidden_state_survives_resize(qtbot):
    window, toolbar, top_buttons, _ = _make_overflow_toolbar(qtbot)
    panel = toolbar._widget
    disabled_button = top_buttons[-1]
    toolbar.disable_widget(disabled_button)

    qtbot.waitUntil(lambda: bool(panel._overflow_hidden))
    assert disabled_button not in panel._overflow_hidden
    assert not panel._overflow_menu_actions[disabled_button].isVisible()

    window.resize(320, 600)
    qtbot.waitUntil(lambda: not panel._overflow_hidden)
    assert not panel._button_dict[disabled_button].isVisible()
    assert not panel._overflow_menu_actions[disabled_button].isVisible()


def test_qt_panel_toolbar_auto_hide_can_be_disabled(qtbot):
    window, toolbar, top_buttons, _ = _make_overflow_toolbar(qtbot, auto_hide=False)
    panel = toolbar._widget
    qtbot.wait(0)

    assert toolbar.auto_hide is False
    assert not panel._overflow_hidden
    assert not panel._overflow_action.isVisible()

    toolbar.auto_hide = True
    qtbot.waitUntil(lambda: bool(panel._overflow_hidden))

    toolbar.auto_hide = False
    assert not panel._overflow_hidden
    assert not panel._overflow_action.isVisible()
    assert all(panel._button_dict[button].isVisible() for button in top_buttons)
    window.close()
