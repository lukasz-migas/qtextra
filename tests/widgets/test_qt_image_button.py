from unittest.mock import patch

import pytest
from qtpy.QtCore import Qt

from qtextra.widgets.qt_button_icon import QtAnimationPlayButton, QtImagePushButton, QtPauseButton


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
