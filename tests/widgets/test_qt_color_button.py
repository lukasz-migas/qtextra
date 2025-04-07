import numpy as np
import pytest

from qtextra.widgets.qt_button_color import QtColorButton, QtColorSwatch


@pytest.fixture
def set_qt_swatch(qtbot):
    """Setup panel"""

    def _widget(color) -> QtColorSwatch:
        widget = QtColorSwatch(initial_color=color)
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtColorSwatch:
    @pytest.mark.parametrize("color", ("#FF0000", (255, 0, 0, 255), (1, 0, 0), (1, 0, 0, 1)))
    def test_init(self, set_qt_swatch, color):
        widget = set_qt_swatch(color)
        np.testing.assert_array_equal(widget.color, np.asarray((1.0, 0.0, 0.0, 1.0)))


@pytest.fixture
def set_qt_button(qtbot):
    """Setup panel"""

    def _widget(color) -> QtColorButton:
        widget = QtColorButton(color=color)
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtColorButton:
    @pytest.mark.parametrize("color", ("#FF0000",))
    def test_init(self, set_qt_button, color):
        widget = set_qt_button(color)
        assert widget.color is not None
