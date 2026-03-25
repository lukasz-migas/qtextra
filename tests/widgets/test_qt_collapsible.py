"""Tests for the collapsible widget."""

from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from qtextra.widgets.qt_collapsible import QtCheckCollapsible


def test_qt_check_collapsible_header_controls(qtbot):
    widget = QtCheckCollapsible("Advanced")
    qtbot.addWidget(widget)

    assert widget.is_checked is False

    widget.checkbox.setChecked(True)
    assert widget.is_checked is True
    assert widget._toggle_btn.isChecked() is True

    widget.setCheckboxVisible(False)
    widget.setIconVisible(False)
    widget.setWarningVisible(False)

    assert widget.checkbox.isHidden() is True
    assert widget.action_btn.isHidden() is True
    assert widget.warning_label.isHidden() is True


def test_qt_check_collapsible_add_row_and_layout(qtbot):
    widget = QtCheckCollapsible("Advanced")
    qtbot.addWidget(widget)

    row_widget = QLabel("Row")
    child_layout = QVBoxLayout()
    child_layout.addWidget(QWidget())

    widget.addRow("Name", row_widget)
    widget.addLayout(child_layout)

    content_layout = widget._content.layout()
    assert content_layout.rowCount() == 2


def test_qt_check_collapsible_add_row_raises_without_form_layout(qtbot):
    widget = QtCheckCollapsible("Advanced")
    qtbot.addWidget(widget)
    widget.setContent(QWidget())

    try:
        widget.addRow("Name", QLabel("Row"))
    except ValueError as exc:
        assert "addRow" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected addRow to reject layouts without addRow support.")
