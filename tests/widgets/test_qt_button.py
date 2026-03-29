import pytest
from qtpy.QtCore import Qt

from qtextra.widgets.qt_button import QtActivePushButton, QtPushButton, QtRichTextButton


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


def test_qt_rich_text_button_uses_rich_text(qtbot):
    widget = QtRichTextButton(text="<b>hello</b>")
    qtbot.addWidget(widget)

    assert widget.text() == "<b>hello</b>"
    assert widget._label.textFormat() == Qt.TextFormat.RichText
