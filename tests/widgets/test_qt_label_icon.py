"""Tests for icon label widgets."""

from __future__ import annotations

import pytest
from qtpy.QtCore import QPointF, QSize, Qt
from qtpy.QtGui import QEnterEvent

import qtextra.helpers as hp
from qtextra.widgets import qt_label_icon as label_icon
from qtextra.widgets.qt_label_icon import (
    QtActiveIcon,
    QtIconLabel,
    QtKeepAspectLabel,
    QtQtaHelpLabel,
    QtQtaLabel,
    QtQtaNotificationLabel,
    QtQtaTooltipLabel,
    QtSeverityLabel,
    QtStateLabel,
    QtValidLabel,
    QtWorkerLabel,
    make_png_label,
)


def _enter_event() -> QEnterEvent:
    return QEnterEvent(QPointF(1, 1), QPointF(1, 1), QPointF(1, 1))


def test_make_png_label_returns_keep_aspect_label(qapp, get_icon_path):
    label = make_png_label(get_icon_path, size=(40, 40))

    assert isinstance(label, QtKeepAspectLabel)
    assert label.minimumWidth() == 40
    assert label.minimumHeight() == 40


def test_qt_keep_aspect_label_updates_path(qapp, qtbot, get_icon_path):
    label = QtKeepAspectLabel(None, get_icon_path)
    qtbot.addWidget(label)

    assert label.path == get_icon_path
    label.setPath(get_icon_path)
    assert label.path == get_icon_path


def test_qt_active_icon_toggles_visibility(qapp, qtbot):
    widget = QtActiveIcon(start=False)
    qtbot.addWidget(widget)
    calls = []
    widget.loading_movie.start = lambda: calls.append("start")
    widget.loading_movie.stop = lambda: calls.append("stop")
    widget.show = lambda: calls.append("show")
    widget.hide = lambda: calls.append("hide")

    assert widget.active is False

    widget.setActive(True)
    assert widget.active is True

    widget.setActive(False)
    assert widget.active is False
    assert calls == ["start", "show", "stop", "hide"]


def test_qt_icon_label_emits_click_signal(qapp, qtbot):
    widget = QtIconLabel("info")
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.evt_clicked, timeout=500):
        qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)


def test_qt_qta_label_sets_icon_and_size(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)

    widget.set_qta("help")
    widget.set_qta_size_preset("large")

    assert widget.pixmap() is not None
    assert widget.minimumSize() == QSize(40, 40)
    assert widget.maximumSize() == QSize(40, 40)
    assert widget._size == QSize(40, 40)
    assert widget.objectName() == ""


def test_qt_qta_label_set_qta_size_preserves_custom_object_name(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)
    widget.set_qta("help")
    widget.setObjectName("custom_name")

    widget.set_qta_size((30, 18))

    assert widget.minimumSize() == QSize(30, 18)
    assert widget.maximumSize() == QSize(30, 18)
    assert widget._size == QSize(30, 18)
    assert widget.objectName() == "custom_name"


def test_qt_qta_label_set_square_qta_size_from_int(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)
    widget.set_qta("help")

    widget.set_qta_size(26)

    assert widget.minimumSize() == QSize(26, 26)
    assert widget.maximumSize() == QSize(26, 26)
    assert widget._size == QSize(26, 26)


def test_qt_qta_label_accepts_tuple_icon_size_and_reports_icon_size(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)
    widget.set_qta("help")

    widget.setIconSize((30, 18))

    assert widget.iconSize() == QSize(30, 18)
    assert widget._size == QSize(30, 18)
    assert widget.pixmap() is not None
    assert widget.pixmap().deviceIndependentSize().toSize() == QSize(30, 18)


def test_qt_qta_label_preset_icon_size_matches_widget_size(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)
    widget.set_qta("help")

    widget.set_qta_size_preset("large")

    assert widget.minimumSize() == QSize(40, 40)
    assert widget.maximumSize() == QSize(40, 40)
    assert widget.iconSize() == QSize(40, 40)
    assert widget.pixmap() is not None
    assert widget.pixmap().deviceIndependentSize().toSize() == QSize(40, 40)


def test_qt_qta_label_pixmap_respects_contents_rect(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)
    widget.set_qta("help")
    widget.set_qta_size_preset("large")
    widget.setMinimumSize(QSize(0, 0))
    widget.setMaximumSize(QSize(26, 14))
    widget.resize(26, 14)
    widget.update()

    assert widget.pixmap() is not None
    assert widget.pixmap().deviceIndependentSize().toSize() == QSize(26, 14)


def test_qt_qta_label_update_qta_preserves_size(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)
    widget.set_qta("help")
    widget.set_qta_size_preset("large")

    widget._update_qta()

    assert widget.minimumSize() == QSize(40, 40)
    assert widget.maximumSize() == QSize(40, 40)
    assert widget._size == QSize(40, 40)


def test_qt_qta_label_ignores_scaled_contents_to_preserve_icon_size(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)
    widget.set_qta("help")
    widget.resize(64, 64)

    widget.setScaledContents(True)
    widget.setIconSize(QSize(18, 18))

    assert widget.hasScaledContents() is False
    assert widget.iconSize() == QSize(18, 18)
    assert widget.pixmap() is not None
    assert widget.pixmap().deviceIndependentSize().toSize() == QSize(18, 18)


def test_qta_size_deprecations_warn_and_preserve_legacy_object_name(qapp, qtbot):
    widget = QtQtaLabel()
    qtbot.addWidget(widget)

    with pytest.deprecated_call(match="set_default_size"):
        widget.set_default_size(large=True)
    assert widget.objectName() == "large_icon"
    assert widget.minimumSize() == QSize(40, 40)
    assert widget._size == QSize(40, 40)

    with pytest.deprecated_call(match="set_large"):
        widget.set_large()
    assert widget.objectName() == "large_icon"

    with pytest.deprecated_call(match="get_icon_size_for_name"):
        object_name, size = QtQtaLabel.get_icon_size_for_name("large")
    assert object_name == "large_icon"
    assert size == (40, 40)


def test_make_qta_helpers_warn_for_legacy_size_flags(qapp, qtbot):
    with pytest.deprecated_call(match="make_qta_btn"):
        button = hp.make_qta_btn(None, "help", large=True)
    qtbot.addWidget(button)
    assert button.minimumSize() == QSize(40, 40)
    assert button.maximumSize() == QSize(40, 40)
    assert button.iconSize() == QSize(32, 32)

    with pytest.deprecated_call(match="make_qta_label"):
        label = hp.make_qta_label(None, "help", large=True)
    qtbot.addWidget(label)
    assert label.minimumSize() == QSize(40, 40)
    assert label.maximumSize() == QSize(40, 40)
    assert label._size == QSize(40, 40)


def test_qt_qta_notification_label_validates_state(qapp, qtbot):
    widget = QtQtaNotificationLabel()
    qtbot.addWidget(widget)

    widget.state = "warning"
    assert widget.state == "warning"

    try:
        widget.state = "bad-state"
    except ValueError as exc:
        assert "Invalid state" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected invalid notification state to raise.")


def test_qt_qta_tooltip_label_shows_tooltip(qapp, monkeypatch, qtbot):
    widget = QtQtaTooltipLabel()
    qtbot.addWidget(widget)
    widget.setToolTip("Tooltip text")

    shown = []
    monkeypatch.setattr(label_icon.QToolTip, "showText", lambda pos, text, parent=None: shown.append((text, parent)))

    widget.enterEvent(_enter_event())

    assert shown == [("Tooltip text", widget)]


def test_qt_qta_help_label_creates_and_clears_dialog(qapp, monkeypatch, qtbot):
    class _DialogSignal:
        def __init__(self):
            self.callback = None

        def connect(self, callback):
            self.callback = callback

    class _DummyDialog:
        def __init__(self, parent, text):
            self.parent = parent
            self.text = text
            self.evt_close = _DialogSignal()
            self.shown_for = None

        def show_right_of_widget(self, widget):
            self.shown_for = widget

    monkeypatch.setattr(label_icon, "InfoDialog", _DummyDialog)

    widget = QtQtaHelpLabel()
    qtbot.addWidget(widget)
    widget.setToolTip("Help text")

    widget.enterEvent(_enter_event())
    assert widget._dlg is not None
    assert widget._dlg.text == "Help text"
    assert widget._dlg.shown_for is widget

    first_dialog = widget._dlg
    widget.enterEvent(_enter_event())
    assert widget._dlg is first_dialog

    widget._removeDialog()
    assert widget._dlg is None


def test_stateful_icon_labels_update_state(qapp, qtbot):
    severity = QtSeverityLabel()
    state = QtStateLabel()
    worker = QtWorkerLabel()
    valid = QtValidLabel()
    qtbot.addWidget(severity)
    qtbot.addWidget(state)
    qtbot.addWidget(worker)
    qtbot.addWidget(valid)

    severity.severity = "error"
    state.state = "check"
    worker.state = "thread"
    valid.state = False

    assert severity.severity == "error"
    assert state.state == "check"
    assert worker.state == "thread"
    assert valid.state is False
    assert severity.pixmap() is not None
    assert state.pixmap() is not None
    assert worker.pixmap() is not None
    assert valid.pixmap() is not None
