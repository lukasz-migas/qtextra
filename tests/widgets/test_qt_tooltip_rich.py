"""Tests for the rich tooltip widget."""

import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QPushButton, QWidget

from qtextra.widgets.qt_tooltip_rich import (
    QtRichToolTip,
    RichToolTipAction,
    RichToolTipData,
    _RichToolTipContent,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parent_widget(qtbot):
    """Create a visible parent widget."""
    w = QWidget()
    w.setMinimumSize(200, 100)
    qtbot.addWidget(w)
    w.show()
    return w


@pytest.fixture
def target_button(qtbot, parent_widget):
    """Create a push-button inside the parent widget."""
    btn = QPushButton("target", parent_widget)
    qtbot.addWidget(btn)
    btn.show()
    return btn


# ---------------------------------------------------------------------------
# RichToolTipData model tests
# ---------------------------------------------------------------------------


class TestRichToolTipData:
    """Tests for the Pydantic data model."""

    def test_defaults(self):
        data = RichToolTipData()
        assert data.title == ""
        assert data.content == ""
        assert data.image is None
        assert data.icon is None
        assert data.shortcut == ""
        assert data.actions == []
        assert data.duration == -1

    def test_with_values(self):
        action = RichToolTipAction(label="Go", callback=lambda: None, object_name="btn")
        data = RichToolTipData(
            title="Hello",
            content="<b>world</b>",
            icon="fa5s.home",
            shortcut="Ctrl+H",
            actions=[action],
            duration=5000,
        )
        assert data.title == "Hello"
        assert data.actions[0].label == "Go"
        assert data.duration == 5000

    def test_action_defaults(self):
        action = RichToolTipAction(label="Click")
        assert action.callback is None
        assert action.object_name == ""


# ---------------------------------------------------------------------------
# _RichToolTipContent tests
# ---------------------------------------------------------------------------


class TestRichToolTipContent:
    """Tests for the internal content frame."""

    def test_minimal_content(self, qtbot):
        content = _RichToolTipContent(title="Title", content="Body")
        qtbot.addWidget(content)
        assert content.objectName() == "richToolTipContent"

    def test_with_icon_and_shortcut(self, qtbot):
        content = _RichToolTipContent(
            title="Title",
            content="Body",
            icon="fa5s.home",
            shortcut="Ctrl+H",
        )
        qtbot.addWidget(content)
        title_labels = content.findChildren(QLabel, "richToolTipTitle")
        assert len(title_labels) == 1
        assert title_labels[0].text() == "Title"

        shortcut_labels = content.findChildren(QLabel, "richToolTipShortcut")
        assert len(shortcut_labels) == 1
        assert shortcut_labels[0].text() == "Ctrl+H"

    def test_with_actions(self, qtbot):
        called = []
        action = RichToolTipAction(label="Run", callback=lambda: called.append(True))
        content = _RichToolTipContent(title="T", actions=[action])
        qtbot.addWidget(content)

        content._on_action(action)
        assert called == [True]

    def test_action_signal(self, qtbot):
        action = RichToolTipAction(label="Sig")
        content = _RichToolTipContent(title="T", actions=[action])
        qtbot.addWidget(content)

        with qtbot.waitSignal(content.evt_action_clicked, timeout=500):
            content._on_action(action)

    def test_link_signal(self, qtbot):
        content = _RichToolTipContent(
            content='Click <a href="https://example.com">here</a>',
        )
        qtbot.addWidget(content)
        body_labels = content.findChildren(QLabel, "richToolTipBody")
        assert len(body_labels) == 1

        with qtbot.waitSignal(content.evt_link_clicked, timeout=500):
            body_labels[0].linkActivated.emit("https://example.com")

    def test_cleanup_without_media(self, qtbot):
        content = _RichToolTipContent(title="T")
        qtbot.addWidget(content)
        content.cleanup()  # should not raise

    def test_size_constraints(self, qtbot):
        content = _RichToolTipContent(title="T", content="C")
        qtbot.addWidget(content)
        assert content.minimumWidth() == _RichToolTipContent._MIN_WIDTH
        assert content.maximumWidth() == _RichToolTipContent._MAX_WIDTH


# ---------------------------------------------------------------------------
# QtRichToolTip tests
# ---------------------------------------------------------------------------


class TestQtRichToolTip:
    """Tests for the tooltip popup window."""

    def test_window_flags(self, qtbot, parent_widget):
        tip = QtRichToolTip.show_tooltip(title="Test", content="Body", parent=parent_widget)
        qtbot.addWidget(tip)

        assert tip.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert tip.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        assert tip.windowFlags() & Qt.WindowType.Tool
        assert tip.windowFlags() & Qt.WindowType.FramelessWindowHint
        tip.close()

    def test_show_and_close(self, qtbot, parent_widget, target_button):
        tip = QtRichToolTip.show_tooltip(
            title="Hi",
            content="World",
            target=target_button,
            parent=parent_widget,
        )
        qtbot.addWidget(tip)
        assert tip.isVisible()

        with qtbot.waitSignal(tip.evt_closed, timeout=1000):
            tip.close()

    def test_singleton_pattern(self, qtbot, parent_widget):
        tip1 = QtRichToolTip.show_tooltip(title="First", content="A", parent=parent_widget)
        qtbot.addWidget(tip1)
        assert QtRichToolTip._active_instance is tip1

        tip2 = QtRichToolTip.show_tooltip(title="Second", content="B", parent=parent_widget)
        qtbot.addWidget(tip2)
        assert QtRichToolTip._active_instance is tip2
        tip2.close()

    def test_dismiss_class_method(self, qtbot, parent_widget):
        tip = QtRichToolTip.show_tooltip(title="Dismiss", content="me", parent=parent_widget)
        qtbot.addWidget(tip)
        assert QtRichToolTip._active_instance is tip

        QtRichToolTip.dismiss()
        qtbot.waitUntil(lambda: QtRichToolTip._active_instance is None, timeout=1000)

    def test_hover_prevents_dismiss(self, qtbot, parent_widget):
        tip = QtRichToolTip.show_tooltip(title="Hover", content="test", parent=parent_widget, duration=50)
        qtbot.addWidget(tip)
        # simulate hover
        tip._hovered = True
        tip._fade_out()
        # should still be visible (fade_out is a no-op while hovered)
        assert tip.windowOpacity() > 0

        tip._hovered = False
        tip.close()

    def test_show_from_data(self, qtbot, parent_widget, target_button):
        data = RichToolTipData(
            title="Model",
            content="<code>hello</code>",
            icon="fa5s.home",
            duration=5000,
        )
        tip = QtRichToolTip.show_from_data(data, target=target_button, parent=parent_widget)
        qtbot.addWidget(tip)
        assert tip.isVisible()
        assert tip._duration == 5000
        tip.close()

    def test_no_target_positions_at_cursor(self, qtbot, parent_widget):
        tip = QtRichToolTip.show_tooltip(title="Cursor", content="pos", parent=parent_widget)
        qtbot.addWidget(tip)
        assert tip.isVisible()
        tip.close()

    def test_code_style_injection(self, qtbot, parent_widget):
        tip = QtRichToolTip.show_tooltip(
            title="Code",
            content="Use <code>foo()</code> to call it.",
            parent=parent_widget,
        )
        qtbot.addWidget(tip)
        body_labels = tip._content.findChildren(QLabel, "richToolTipBody")
        assert len(body_labels) == 1
        html = body_labels[0].text()
        # code style should have been injected
        assert "background:" in html
        assert "color:" in html
        tip.close()

    def test_enter_leave_events(self, qtbot, parent_widget):
        tip = QtRichToolTip.show_tooltip(title="EL", content="test", parent=parent_widget, duration=100)
        qtbot.addWidget(tip)

        # simulate enter — should stop timers
        tip.enterEvent(None)
        assert tip._hovered is True
        assert not tip._dismiss_timer.isActive()
        assert not tip._leave_timer.isActive()

        # simulate leave — should start leave timer
        tip.leaveEvent(None)
        assert tip._hovered is False
        assert tip._leave_timer.isActive()

        tip.close()
