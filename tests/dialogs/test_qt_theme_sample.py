from __future__ import annotations

from qtextra.dialogs.qt_theme_sample import QtSampleWidget
from qtextra.widgets.qt_button_progress import QtActiveProgressBarButton
from qtextra.widgets.qt_button_tag import QtTagManager
from qtextra.widgets.qt_filter_edit import QtFilterEdit
from qtextra.widgets.qt_label_read_more import QReadMoreLessLabel
from qtextra.widgets.qt_notification_badge import QtNotificationBadge
from qtextra.widgets.qt_toggle_group import QtToggleGroup


def test_qt_theme_sample_includes_qtextra_widgets(qtbot):
    widget = QtSampleWidget()
    qtbot.addWidget(widget)

    assert widget.findChildren(QtToggleGroup)
    assert widget.findChildren(QtFilterEdit)
    assert widget.findChildren(QtTagManager)
    assert widget.findChildren(QtActiveProgressBarButton)
    assert widget.findChildren(QtNotificationBadge)
    assert widget.findChildren(QReadMoreLessLabel)
