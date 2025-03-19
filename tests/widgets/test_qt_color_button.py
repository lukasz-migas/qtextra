import numpy as np
import pytest
from qtextra.widgets.qt_button_color import QtColorSwatch


@pytest.fixture
def setup_widget(qtbot):
    """Setup panel"""

    def _widget(color) -> QtColorSwatch:
        widget = QtColorSwatch(initial_color=color)
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtColorSwatch:
    @pytest.mark.parametrize("color", ("#FF0000", (255, 0, 0, 255), (1, 0, 0), (1, 0, 0, 1)))
    def test_init(self, setup_widget, color):
        widget = setup_widget(color)
        np.testing.assert_array_equal(widget.color, np.asarray((1.0, 0.0, 0.0, 1.0)))
