from unittest.mock import patch

import pytest

from qtextra.config.events import EVENTS
from qtextra.widgets.qt_splash_screen import QtSplashScreen


@pytest.fixture
def setup_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtSplashScreen:
        widget = QtSplashScreen()
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtSplashScreen:
    def test_init(self, qtbot, setup_widget, monkeypatch):
        monkeypatch.setattr(QtSplashScreen, "show", lambda *a: None)
        widget = setup_widget()

        with patch.object(widget, "on_message") as mock_method:
            EVENTS.evt_splash_msg.emit("Hello")
            mock_method.assert_called_once()
