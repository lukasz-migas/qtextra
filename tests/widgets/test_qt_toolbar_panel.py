import pytest
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QColor, QContextMenuEvent
from qtpy.QtWidgets import QApplication, QMainWindow, QWidget

from qtextra.config import THEMES
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


@pytest.mark.parametrize("preset, button_size", [("16px", 16), ("24px", 24), ("large", 40), ("60px", 60)])
@pytest.mark.parametrize("title", [None, "Home"])
def test_themed_panel_toolbar_size_follows_preset(qtbot, preset, button_size, title):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.setStyleSheet(THEMES.get_theme_stylesheet("dark"))
    window.resize(320, 400)
    toolbar = QtPanelToolbar(window, size_preset=preset)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    button = toolbar.add_widget("home", title=title)
    source = button.image_btn if title else button
    window.show()

    qtbot.waitUntil(lambda: toolbar.width() == toolbar.sizeHint().width())
    assert source.size().width() == button_size
    assert source.size().height() == button_size
    assert toolbar.width() <= button_size + 10
    assert toolbar._widget._overflow_button.sizeHint().width() == button_size


def test_themed_panel_toolbar_respects_button_size_override(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.setStyleSheet(THEMES.get_theme_stylesheet("dark"))
    toolbar = QtPanelToolbar(window, size_preset="16px")
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    small = toolbar.add_widget("home")
    large = toolbar.add_widget("gear", title="Settings", size_preset="40px")
    window.show()

    qtbot.waitUntil(lambda: toolbar.width() == toolbar.sizeHint().width())
    assert small.sizeHint().width() == 16
    assert large.image_btn.size().width() == 40
    assert large.label.width() == 40
    assert small.width() == large.width() == 40
    toolbar.disable_widget(large)
    qtbot.waitUntil(lambda: small.width() == 16 and toolbar.width() <= 26)


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


def test_qt_panel_toolbar_overflow_update_reshows_bottom_buttons_immediately(qtbot):
    window, toolbar, _top_buttons, bottom_buttons = _make_overflow_toolbar(qtbot, height=240)
    panel = toolbar._widget
    qtbot.waitUntil(lambda: bool(panel._overflow_hidden))

    # shrinking makes QToolBar hide the trailing (bottom) widgets until the next layout pass
    window.resize(320, 160)
    panel._buttons.layout().activate()
    assert not any(button.isVisible() for button in bottom_buttons)

    panel._update_overflow()
    assert panel._overflow_hidden
    assert all(button.isVisible() for button in bottom_buttons)


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


def test_qt_labelled_toolbar_push_button_active_property_tracks_checked_state(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.setStyleSheet(THEMES.get_theme_stylesheet("dark"))
    toolbar = QtPanelToolbar(window, label_hidden=False)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    first = toolbar.add_widget("home", title="Home", widget=QWidget())
    second = toolbar.add_widget("gear", title="Settings", widget=QWidget())
    window.show()

    assert first.property("active") is True
    assert second.property("active") is False

    qtbot.mouseClick(second.image_btn, Qt.MouseButton.LeftButton)
    assert first.property("active") is False
    assert second.property("active") is True


def test_qt_labelled_toolbar_push_button_label_click_activates_panel(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=False)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    toolbar.add_widget("home", title="Home", widget=QWidget())
    settings_panel = QWidget()
    settings_button = toolbar.add_widget("gear", title="Settings", widget=settings_panel)
    window.show()

    qtbot.mouseClick(settings_button.label, Qt.MouseButton.LeftButton)
    assert toolbar.stack_widget.currentWidget() is settings_panel
    assert settings_button.isChecked()
    assert settings_button.property("active") is True


def _count_success_columns(widget, theme: str) -> set[int]:
    """Return the x positions of pixels painted in `theme`'s success colour."""
    image = widget.grab().toImage()
    ratio = image.devicePixelRatio()
    # read the colour from the theme under test - the active theme may differ (and other tests modify it)
    success = QColor(THEMES[theme].success.as_hex(format="long")).rgb()
    return {
        int(x / ratio)
        for x in range(image.width())
        for y in range(0, image.height(), 2)
        if image.pixelColor(x, y).rgb() == success
    }


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qt_labelled_toolbar_push_button_single_active_bar_when_connected_late(qtbot, theme):
    """Panels connected after the button was polished must not show a second bar on the icon."""
    window = QMainWindow()
    qtbot.addWidget(window)
    window.setStyleSheet(THEMES.get_theme_stylesheet(theme))
    toolbar = QtPanelToolbar(window, label_hidden=False, size_preset="40px")
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    button = toolbar.add_widget("gear", title="Feature\nViewer", func=lambda *_: None)
    window.show()
    qtbot.waitExposed(window)

    toolbar.connect_widget("gear", QWidget())
    assert button.isChecked()
    columns = _count_success_columns(button, theme)
    assert columns, "active bar is not painted"
    assert max(columns) < 3, f"success colour painted outside the wrapper bar: {sorted(columns)}"


def test_qt_labelled_toolbar_push_button_wrapper_drives_tooltip_and_pulse(qtbot):
    widget = QtLabelledToolbarPushButton()
    qtbot.addWidget(widget)
    widget.set_label("Settings")
    widget.setRichToolTip("Settings", "Configure things")

    # tooltip text lives on the icon button but is anchored to the whole tile
    assert widget.image_btn._title == "Settings"
    assert widget.image_btn._tooltip_target is widget
    QApplication.sendEvent(widget, QEvent(QEvent.Type.Enter))
    assert widget.image_btn.tooltip_timer.isActive()
    QApplication.sendEvent(widget, QEvent(QEvent.Type.Leave))
    assert not widget.image_btn.tooltip_timer.isActive()

    # the pulse effect fades icon and label together
    assert widget.graphicsEffect() is widget.image_btn.opacity
    assert widget.image_btn.graphicsEffect() is None


def test_qt_labelled_toolbar_push_button_forwards_button_api(qtbot):
    widget = QtLabelledToolbarPushButton()
    qtbot.addWidget(widget)
    widget.set_qta("gear")
    widget.setCheckable(True)

    assert widget.isCheckable()
    assert not widget.icon().isNull()
    calls = []
    widget.evt_click.connect(lambda *_: calls.append("click"))
    widget.on_click()
    assert calls == ["click"]


def _context_menu_at(panel, widget) -> None:
    """Send a right-click context menu event to `panel` at the centre of `widget`."""
    pos = widget.mapTo(panel, widget.rect().center())
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos, panel.mapToGlobal(pos))
    QApplication.sendEvent(panel, event)


def test_qt_panel_toolbar_toggle_titles_action(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=True)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    button = toolbar.add_widget("gear", title="Settings")
    window.show()

    action = toolbar.toggle_titles_action
    assert action in toolbar.context_menu.actions()
    assert action.isCheckable() and not action.isChecked()

    action.trigger()
    assert not toolbar.label_hidden
    assert not button.label.isHidden()

    toolbar.label_hidden = True
    assert not action.isChecked()
    assert button.label.isHidden()


def test_qt_panel_toolbar_right_click_shows_context_menu(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=False)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    button = toolbar.add_widget("gear", title="Settings", widget=QWidget())
    custom = toolbar.add_widget("help", title="Help")
    custom.connect_to_right_click(lambda *_: None)
    window.show()
    qtbot.waitExposed(window)
    panel, menu = toolbar._widget, toolbar.context_menu

    # the label is part of the button tile too
    _context_menu_at(panel, button.label)
    qtbot.waitUntil(menu.isVisible)
    menu.close()

    # buttons with their own right-click handler do not get the toolbar menu
    _context_menu_at(panel, custom.image_btn)
    assert not menu.isVisible()


@pytest.mark.parametrize("title", [None, "Settings"])
def test_qt_panel_toolbar_lazy_panel_activates_on_first_click(qtbot, title):
    """A panel connected from the button's own click callback (lazy creation) shows on the first click."""
    window = QMainWindow()
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=False)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    window.setCentralWidget(toolbar.stack_widget)
    panels: dict[str, QWidget] = {}

    def _lazy(name: str, *_) -> None:
        if name not in panels:
            panels[name] = QWidget()
            toolbar.connect_widget(name, panels[name])

    buttons = {
        name: toolbar.add_widget(name, title=title and f"{title} {name}", func=lambda *_, n=name: _lazy(n))
        for name in ("home", "gear")
    }
    window.show()
    qtbot.waitExposed(window)

    for name in ("home", "gear", "home"):
        button = buttons[name]
        qtbot.mouseClick(button.image_btn if title else button, Qt.MouseButton.LeftButton)
        assert toolbar.stack_widget.currentWidget() is panels[name], name
        assert toolbar.stack_widget.isVisible()
        assert button.isChecked()
        assert not buttons["gear" if name == "home" else "home"].isChecked()


@pytest.mark.xfail(reason="Fails on CI.")
def test_qt_panel_toolbar_elided_labels_use_shared_tile_width(qtbot):
    """Elided labels only elide when they do not fit the (shared) tile width, not the icon width."""
    window = QMainWindow()
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=False, size_preset="40px")
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    toolbar.add_widget("home", title="Unsupervised\nLearning", elide=False)
    elided = toolbar.add_widget("gear", title="Import\nWizard", location="bottom")
    too_long = toolbar.add_widget("help", title="Multi-dataset\nBuilder with a very long name", location="bottom")
    window.show()
    qtbot.waitExposed(window)

    qtbot.waitUntil(lambda: elided.label.text() == "Import\nWizard")
    assert elided.label.width() <= elided.width()
    assert elided.sizeHint().width() == elided.image_btn.sizeHint().width()
    # text wider than the tile is still elided
    assert too_long.label.text().splitlines()[0] == "Multi-dataset"
    assert "\N{HORIZONTAL ELLIPSIS}" in too_long.label.text().splitlines()[1]
    assert too_long.label.width() <= too_long.width()


def test_qt_panel_toolbar_elided_labels_shrink_with_shared_width(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    toolbar = QtPanelToolbar(window, label_hidden=False, size_preset="40px")
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    wide = toolbar.add_widget("home", title="Unsupervised Learning", elide=False)
    elided = toolbar.add_widget("gear", title="Import Wizard", location="bottom")
    window.show()
    qtbot.waitUntil(lambda: elided.label.text() == "Import Wizard")

    toolbar.disable_widget(wide)
    icon_width = elided.image_btn.sizeHint().width()
    qtbot.waitUntil(lambda: elided.width() == icon_width)
    assert elided.label.width() <= icon_width
    assert "\N{HORIZONTAL ELLIPSIS}" in elided.label.text()


def test_qt_labelled_toolbar_push_button_active_label_is_bold(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.setStyleSheet(THEMES.get_theme_stylesheet("light"))
    toolbar = QtPanelToolbar(window, label_hidden=False)
    window.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)
    first = toolbar.add_widget("home", title="Home", widget=QWidget())
    second = toolbar.add_widget("gear", title="Settings", widget=QWidget(), elide=False)
    window.show()
    width = second.label.width()

    assert first.label.font().bold()
    assert not second.label.font().bold()

    qtbot.mouseClick(second.image_btn, Qt.MouseButton.LeftButton)
    assert not first.label.font().bold()
    assert second.label.font().bold()
    # label width is reserved for bold text, so activating does not shift the layout
    assert second.label.width() == width
