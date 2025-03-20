from unittest.mock import patch

import pytest
from qtpy.QtCore import Qt

from qtextra.widgets.qt_button_icon import QtImagePushButton


@pytest.fixture
def setup_image_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtImagePushButton:
        widget = QtImagePushButton()
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
