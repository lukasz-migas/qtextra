import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QImage

from qtextra.config import THEMES
from qtextra.widgets.qt_button import QtActivePushButton, QtPushButton, QtRichTextButton


def _count_matching_pixels(image: QImage, color: QColor, x_range: range, y_range: range) -> int:
    """Return the number of pixels matching color inside the ranges."""
    count = 0
    for y in y_range:
        for x in x_range:
            if image.pixelColor(x, y).rgb() == color.rgb():
                count += 1
    return count


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


class TestQtPushButton:
    def test_text_and_word_wrap(self, qtbot):
        widget = QtPushButton(text="hello")
        qtbot.addWidget(widget)

        assert widget.text() == "hello"

        widget.setWordWrap(True)

        assert widget._label.wordWrap() is True

    def test_right_click_signal(self, qtbot):
        widget = QtPushButton(text="hello")
        qtbot.addWidget(widget)
        seen = []
        widget.connect_to_right_click(lambda: seen.append("right"))

        qtbot.mouseClick(widget, Qt.MouseButton.RightButton)

        assert seen == ["right"]
        assert widget.has_right_click is True
        assert widget.property("right_click") is True

    def test_right_click_corner_renders_at_bottom_right(self, qtbot):
        widget = QtPushButton(text="Create GeoJSON directory\n(template)")
        widget.setFixedSize(460, 52)
        widget.has_right_click = True
        qtbot.addWidget(widget)

        image = QImage(widget.size(), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        widget.render(image)

        success = QColor(THEMES.get_hex_color("success"))
        bottom_right_pixels = _count_matching_pixels(
            image,
            success,
            range(widget.width() - 24, widget.width()),
            range(widget.height() - 24, widget.height()),
        )
        top_right_pixels = _count_matching_pixels(
            image,
            success,
            range(widget.width() - 60, widget.width()),
            range(24),
        )

        assert bottom_right_pixels > 0
        assert top_right_pixels == 0


def test_qt_rich_text_button_uses_rich_text(qtbot):
    widget = QtRichTextButton(text="<b>hello</b>")
    qtbot.addWidget(widget)

    assert widget.text() == "<b>hello</b>"
    assert widget._label.textFormat() == Qt.TextFormat.RichText
