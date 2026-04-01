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


def test_qt_labelled_toolbar_push_button_preserves_explicit_multiline_labels(qtbot):
    widget = QtLabelledToolbarPushButton()
    qtbot.addWidget(widget)

    widget.set_default_size(large=True)
    widget.set_label("First line\nSecond line")

    assert widget.label.text().count("\n") == 1
    assert widget.label.height() > widget.label.fontMetrics().lineSpacing()


def test_qt_labelled_toolbar_push_button_can_disable_elision(qtbot):
    widget = QtLabelledToolbarPushButton(elide=False)
    qtbot.addWidget(widget)

    widget.set_default_size(large=True)
    widget.set_label("Very long label")

    assert widget.elide is False
    assert "..." not in widget.label.text()
    assert widget.label.width() > widget.image_btn.sizeHint().width()


def test_qt_panel_toolbar_add_widget_passes_elide_flag(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    button = toolbar.add_widget("gear", title="Very long label", elide=False)

    assert isinstance(button, QtLabelledToolbarPushButton)
    assert button.elide is False
    assert button.label.width() > button.image_btn.sizeHint().width()


def test_qt_panel_toolbar_centers_buttons_when_non_elided_label_expands_width(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    plain_button = toolbar.add_widget("home")
    wide_button = toolbar.add_widget("gear", title="Very long label", elide=False)

    assert plain_button.width() == wide_button.width()
