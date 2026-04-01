from qtextra.widgets.qt_button_icon import QtLabelledToolbarPushButton
from qtextra.widgets.qt_toolbar_panel import QtPanelToolbar


def test_qt_labelled_toolbar_push_button_constrains_label_width(qtbot):
    widget = QtLabelledToolbarPushButton()
    qtbot.addWidget(widget)

    widget.set_default_size(large=True)
    widget.set_label("Very long toolbar label that should not widen the whole toolbar")
    icon_width = widget.image_btn.sizeHint().width()

    assert widget.label.wordWrap() is False
    assert widget.label.width() <= icon_width
    assert widget.label.height() <= widget.label.fontMetrics().lineSpacing() + 1
    assert widget.sizeHint().width() <= icon_width


def test_qt_panel_toolbar_label_hidden_propagates_to_labelled_buttons(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    button = toolbar.add_widget("gear", title="Very long toolbar label")
    icon_width = button.image_btn.sizeHint().width()

    assert isinstance(button, QtLabelledToolbarPushButton)
    assert button.label_hidden is False
    assert button.sizeHint().width() <= icon_width

    toolbar.label_hidden = True

    assert button.label_hidden is True
