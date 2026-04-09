import pytest
from qtpy.QtWidgets import QWidget

from qtextra.widgets.qt_button_icon import QtLabelledToolbarPushButton
from qtextra.widgets.qt_toolbar_panel import QtPanelToolbar


def test_qt_labelled_toolbar_push_button_constrains_label_width(qtbot):
    widget = QtLabelledToolbarPushButton()
    qtbot.addWidget(widget)

    widget.set_qta_size_preset("large")
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

    widget.set_qta_size_preset("large")
    widget.set_label("First line\nSecond line")

    assert widget.label.text().count("\n") == 1
    assert widget.label.height() > widget.label.fontMetrics().lineSpacing()


def test_qt_labelled_toolbar_push_button_can_disable_elision(qtbot):
    widget = QtLabelledToolbarPushButton(elide=False)
    qtbot.addWidget(widget)

    widget.set_qta_size_preset("large")
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


def test_qt_panel_toolbar_rejects_duplicate_button_names(qtbot):
    toolbar = QtPanelToolbar()
    qtbot.addWidget(toolbar)

    toolbar.add_widget("home")

    with pytest.raises(ValueError, match="already exists"):
        toolbar.add_widget("home")


def test_qt_panel_toolbar_disabling_active_button_switches_to_another_panel(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    home_panel = QWidget()
    settings_panel = QWidget()

    home_button = toolbar.add_widget("home", widget=home_panel)
    settings_button = toolbar.add_widget("gear", widget=settings_panel)
    settings_button.click()

    toolbar.disable_widget(settings_button)

    assert toolbar.stack_widget.currentWidget() is home_panel
    assert settings_button.isChecked() is False
    assert home_button.isChecked() is True


def test_qt_panel_toolbar_hiding_wide_button_reduces_shared_width(qtbot):
    toolbar = QtPanelToolbar(label_hidden=False)
    qtbot.addWidget(toolbar)

    plain_button = toolbar.add_widget("home")
    wide_button = toolbar.add_widget("gear", title="Very long label", elide=False)
    expanded_width = plain_button.width()

    toolbar.disable_widget(wide_button)

    assert plain_button.width() < expanded_width
