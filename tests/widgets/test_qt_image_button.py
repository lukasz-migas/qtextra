from unittest.mock import Mock, patch

import pytest
from qtpy.QtCore import QEvent, Qt

from qtextra.widgets.qt_button_icon import (
    PRESET_TO_BADGE_SIZE,
    QtAnimationPlayButton,
    QtImagePushButton,
    QtPauseButton,
    QtPriorityButton,
    QtToolbarPushButton,
)
from qtextra.widgets.qt_notification_badge import QtNotificationBadge


@pytest.fixture
def setup_image_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtImagePushButton:
        widget = QtImagePushButton()
        qtbot.addWidget(widget)
        return widget

    return _widget


@pytest.fixture
def setup_animation_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtAnimationPlayButton:
        widget = QtAnimationPlayButton()
        qtbot.addWidget(widget)
        return widget

    return _widget


@pytest.fixture
def setup_pause_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtPauseButton:
        widget = QtPauseButton()
        qtbot.addWidget(widget)
        return widget

    return _widget


@pytest.fixture
def setup_toolbar_widget(qtbot):
    """Setup toolbar button."""

    def _widget() -> QtToolbarPushButton:
        widget = QtToolbarPushButton()
        widget.setToolTip("tip")
        qtbot.addWidget(widget)
        widget.show()
        return widget

    return _widget


@pytest.fixture
def setup_priority_widget(qtbot):
    """Setup priority button."""

    def _widget(*, auto_show_menu_on_hover: bool = True) -> QtPriorityButton:
        widget = QtPriorityButton(auto_show_menu_on_hover=auto_show_menu_on_hover)
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtImagePushButton:
    right_click = 0

    def _on_right_click(self):
        self.right_click += 1

    def test_init(self, qtbot, setup_image_widget):
        widget = setup_image_widget()
        widget.setObjectName("info")
        assert widget

        with patch.object(widget, "on_click") as mock_click:
            qtbot.mouseClick(widget, Qt.LeftButton)
            mock_click.assert_called_once()

        with patch.object(widget, "on_right_click") as mock_click:
            qtbot.mouseClick(widget, Qt.RightButton)
            mock_click.assert_called_once()

        widget.connect_to_right_click(self._on_right_click)
        qtbot.mouseClick(widget, Qt.RightButton)
        assert self.right_click == 1

    def test_set_count_attaches_badge_in_count_mode(self, setup_image_widget):
        widget = setup_image_widget()
        widget.set_count(5)

        assert isinstance(widget._badge, QtNotificationBadge)
        assert widget._badge.mode == "count"
        assert widget._badge.count == 5
        assert widget._badge.state == "info"
        assert widget.count_enabled is True

    def test_set_count_caps_display_at_99_plus(self, setup_image_widget):
        widget = setup_image_widget()
        widget.set_count(150)

        assert widget._badge.count == 150
        assert widget._badge._display_text == "99+"

    def test_set_count_disabled_hides_badge(self, setup_image_widget):
        widget = setup_image_widget()
        widget.set_count(3)
        widget.set_count(0, enabled=False)

        assert widget._badge.state == ""
        assert widget.count_enabled is False

    def test_set_badge_dot_mode(self, setup_image_widget):
        widget = setup_image_widget()
        widget.set_badge(state="warning", mode="dot")

        assert widget._badge.state == "warning"
        assert widget._badge.mode == "dot"

    def test_clear_badge_resets_state(self, setup_image_widget):
        widget = setup_image_widget()
        widget.set_count(2)
        widget.clear_badge()

        assert widget.count == 0
        assert widget.count_enabled is False
        assert widget._badge.state == ""

    @pytest.mark.parametrize(
        ("preset", "expected"),
        [
            ("xxsmall", "xs"),
            ("small", "sm"),
            ("normal", "md"),
            ("large", "lg"),
            ("xxlarge", "xl"),
        ],
    )
    def test_preset_syncs_badge_size(self, setup_image_widget, preset, expected):
        widget = setup_image_widget()
        widget.set_count(1)
        widget.set_qta_size_preset(preset)

        assert widget._badge.badge_size == expected
        assert PRESET_TO_BADGE_SIZE[preset] == expected

    def test_button_grows_when_badge_attached(self, setup_image_widget):
        widget = setup_image_widget()
        base = widget.maximumSize()

        widget.set_count(5)
        grown = widget.maximumSize()

        assert grown.width() > base.width()
        assert grown.height() > base.height()

    def test_button_shrinks_back_when_badge_cleared(self, setup_image_widget):
        widget = setup_image_widget()
        base = widget.maximumSize()
        widget.set_count(5)
        widget.clear_badge()

        assert widget.maximumSize() == base


class TestQtAnimationPlayButton:
    def test_init(self, qtbot, setup_animation_widget):
        widget = setup_animation_widget()
        assert widget.playing is False
        widget.playing = True
        assert widget.playing is True


class TestQtPauseButton:
    def test_init(self, qtbot, setup_pause_widget):
        widget = setup_pause_widget()
        assert widget.paused is False
        widget.paused = True
        assert widget.paused is True


class TestQtToolbarPushButton:
    def test_click_suppresses_hover_tooltip_until_leave(self, qtbot, setup_toolbar_widget):
        widget = setup_toolbar_widget()

        widget.event(QEvent(QEvent.Type.Enter))
        assert widget.tooltip_timer.isActive() is True

        qtbot.mouseClick(widget, Qt.LeftButton)

        assert widget.tooltip_timer.isActive() is False
        assert widget._suppress_hover_tooltip is True

        widget.event(QEvent(QEvent.Type.Enter))
        assert widget.tooltip_timer.isActive() is False

        widget.event(QEvent(QEvent.Type.Leave))
        assert widget._suppress_hover_tooltip is False

        widget.event(QEvent(QEvent.Type.Enter))
        assert widget.tooltip_timer.isActive() is True


class TestQtMultiStatePushButton:
    def test_enter_event_shows_menu_on_hover_by_default(self, setup_priority_widget):
        widget = setup_priority_widget()

        with patch.object(widget, "set_and_show_menu") as mock_set_and_show_menu:
            widget.event(QEvent(QEvent.Type.Enter))

        mock_set_and_show_menu.assert_called_once()

    def test_enter_event_does_not_show_menu_when_hover_popup_disabled_in_init(self, setup_priority_widget):
        widget = setup_priority_widget(auto_show_menu_on_hover=False)

        with patch.object(widget, "set_and_show_menu") as mock_set_and_show_menu:
            widget.event(QEvent(QEvent.Type.Enter))

        mock_set_and_show_menu.assert_not_called()

    def test_setter_disables_hover_popup_and_leave_event_remains_safe(self, setup_priority_widget):
        widget = setup_priority_widget()
        widget.set_auto_show_menu_on_hover(False)

        with patch.object(widget, "set_and_show_menu") as mock_set_and_show_menu:
            widget.event(QEvent(QEvent.Type.Enter))

        mock_set_and_show_menu.assert_not_called()

        # When hover is disabled, leaveEvent should NOT close the menu
        # (the menu was opened by click and the user needs to reach it)
        menu = Mock()
        widget._menu = menu
        widget.event(QEvent(QEvent.Type.Leave))

        menu.close.assert_not_called()
        assert widget._menu is menu
