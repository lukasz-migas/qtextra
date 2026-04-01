from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QWidget

from qtextra.widgets.qt_rich_tooltip import QtRichToolTip, RichToolTipAction


def test_qt_rich_tooltip_is_non_activating(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    target = QLabel("target", host)

    tooltip = QtRichToolTip(title="Title", content="Content", target=target, parent=host)

    assert tooltip.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating) is True
    assert tooltip.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert bool(tooltip.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)


def test_qt_rich_tooltip_emits_action_signal_and_callback(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    calls = []

    tooltip = QtRichToolTip(
        title="Title",
        content="Content",
        actions=[RichToolTipAction("Run", callback=lambda: calls.append("callback"))],
        parent=host,
    )
    qtbot.addWidget(tooltip)
    actions = tooltip.findChildren(QWidget, "richToolTipAction")

    seen = []
    tooltip.evt_action_clicked.connect(seen.append)
    actions[0].click()

    assert seen == ["Run"]
    assert calls == ["callback"]


def test_qt_rich_tooltip_emits_link_signal(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    tooltip = QtRichToolTip(content='<a href="https://example.com">Example</a>', parent=host)

    seen = []
    tooltip.evt_link_clicked.connect(seen.append)
    body = tooltip.findChild(QLabel, "richToolTipBody")
    body.linkActivated.emit("https://example.com")

    assert seen == ["https://example.com"]


def test_qt_rich_tooltip_hides_invalid_media(qtbot, tmp_path):
    host = QWidget()
    qtbot.addWidget(host)

    invalid = str(tmp_path / "missing.png")
    tooltip = QtRichToolTip(title="Title", image=invalid, parent=host)

    media = tooltip.findChild(QLabel, "richToolTipMedia")
    assert media is not None
    assert media.isHidden() is True


def test_qt_rich_tooltip_show_tooltip_returns_visible_instance(qtbot):
    host = QWidget()
    qtbot.addWidget(host)

    tooltip = QtRichToolTip.show_tooltip(title="Title", content="Content", parent=host, duration=-1)

    assert isinstance(tooltip, QtRichToolTip)
    assert tooltip.isVisible() is True
    tooltip.close()
