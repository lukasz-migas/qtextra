from pathlib import Path
from unittest.mock import patch

import pytest

from qtextra.config.events import EVENTS
from qtextra.widgets.qt_splash_screen import QtSplashScreen


@pytest.fixture
def setup_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtSplashScreen:
        path = Path(__file__).parent / "_test_data" / "qtextra.png"
        widget = QtSplashScreen(path)
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtSplashScreen:
    def test_init(self, qtbot, setup_widget, monkeypatch):
        monkeypatch.setattr(QtSplashScreen, "show", lambda *a: None)
        widget = setup_widget()

        with qtbot.waitSignal(EVENTS.evt_splash_msg, timeout=500), patch.object(widget, "on_message"):
            EVENTS.evt_splash_msg.emit("Hello")
