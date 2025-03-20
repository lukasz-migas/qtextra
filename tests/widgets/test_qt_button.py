import pytest

from qtextra.widgets.qt_button import QtActivePushButton


@pytest.fixture
def setup_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtActivePushButton:
        widget = QtActivePushButton("")
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtActivePushButton:
    def test_init(self, setup_widget):
        widget = setup_widget()
        assert widget.active is False
        assert widget._pixmap is None
        widget.active = True
        assert widget.active is True
        assert widget._pixmap is not None
