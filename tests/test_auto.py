"""Tests for automatic widget generation helpers."""

from qtpy import QtWidgets as Qw

from qtextra.auto import (
    _append_widgets,
    _insert_after_widget,
    _insert_before_widget,
    get_data_for_widgets,
    get_value_from_widget,
    get_widget_for_schema,
    guess_widget_cls,
    set_value_to_widget,
    set_values_from_dict,
)
from qtextra.widgets.qt_toggle_group import QtToggleGroup


def test_guess_widget_cls_handles_common_schema_shapes():
    assert guess_widget_cls({"type": "string"}) == "line_edit"
    assert guess_widget_cls({"type": "string", "enum": ["A", "B"]}) == "combo_box"
    assert guess_widget_cls({"type": "array", "enum": ["A", "B"]}) == "multi_combo_box"
    assert guess_widget_cls({"type": "boolean"}) == "checkbox"
    assert guess_widget_cls({"type": "integer"}) == "int_spin_box"
    assert guess_widget_cls({"type": "number"}) == "double_spin_box"
    assert guess_widget_cls({"anyOf": [{"type": "string"}]}) == "line_edit"


def test_guess_widget_cls_rejects_unknown_types():
    try:
        guess_widget_cls({"type": "object"})
    except ValueError as exc:
        assert "object" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected unsupported schema types to raise.")


def test_get_widget_for_schema_builds_hidden_line_edit_with_metadata(qapp, qtbot):
    parent = Qw.QWidget()
    qtbot.addWidget(parent)
    widget, layout = get_widget_for_schema(
        parent,
        {
            "type": "string",
            "default": "Alpha",
            "regex": "^[A-Z][a-z]+$",
            "show": False,
            "warning": "Needs attention",
            "help": "Helpful context",
            "info": "Additional info",
        },
    )
    assert isinstance(widget, Qw.QLineEdit)
    assert widget.text() == "Alpha"
    assert widget.isHidden() is True
    assert widget.validator() is not None
    assert layout is not None
    assert layout.count() == 4


def test_get_widget_for_schema_builds_toggle_group(qapp, qtbot):
    parent = Qw.QWidget()
    qtbot.addWidget(parent)
    widget, layout = get_widget_for_schema(
        parent,
        {
            "widget_cls": "single_toggle",
            "options": ["One", "Two"],
            "value": "Two",
        },
    )

    assert isinstance(widget, QtToggleGroup)
    assert widget.value == "Two"
    assert layout is None


def test_get_and_set_value_for_supported_widgets(qapp, qtbot):
    line_edit = Qw.QLineEdit()
    label = Qw.QLabel()
    checkbox = Qw.QCheckBox()
    spinbox = Qw.QSpinBox()
    combo = Qw.QComboBox()
    combo.addItems(["None", "Alpha", "Beta"])
    toggle = QtToggleGroup(None, options=["Red", "Blue"], value="Red")
    qtbot.addWidget(toggle)

    set_value_to_widget(line_edit, ["A", "B"])
    set_value_to_widget(label, None)
    set_value_to_widget(checkbox, 1)
    set_value_to_widget(spinbox, 5)
    set_value_to_widget(combo, "")
    set_value_to_widget(toggle, "Blue")

    assert get_value_from_widget(line_edit) == "A,B"
    assert get_value_from_widget(label) == ""
    assert get_value_from_widget(checkbox) is True
    assert get_value_from_widget(spinbox) == 5
    assert get_value_from_widget(combo) == "None"
    assert get_value_from_widget(toggle) == "Blue"


def test_set_values_from_dict_blocks_signals_by_default(qapp, qtbot):
    widget = Qw.QLineEdit()
    qtbot.addWidget(widget)
    seen = []
    widget.textChanged.connect(seen.append)

    set_values_from_dict({"name": "Alpha"}, {"name": widget})
    assert widget.text() == "Alpha"
    assert seen == []

    set_values_from_dict({"name": "Beta"}, {"name": widget}, block=False)
    assert seen[-1] == "Beta"


def test_get_data_for_widgets_skips_private_entries(qapp, qtbot):
    public_widget = Qw.QLineEdit()
    private_widget = Qw.QLineEdit()
    qtbot.addWidget(public_widget)
    qtbot.addWidget(private_widget)

    public_widget.setText("value")
    private_widget.setText("hidden")

    data = get_data_for_widgets({"name": public_widget, "_internal": private_widget}, extra=1)
    assert data == {"name": "value", "extra": 1}


def test_append_widgets_inserts_after_search_widget(qapp, qtbot):
    parent = Qw.QWidget()
    layout = Qw.QFormLayout(parent)
    first = Qw.QLineEdit()
    second = Qw.QLineEdit()
    qtbot.addWidget(parent)
    layout.addRow("First", first)
    layout.addRow("Second", second)

    _append_widgets(parent, layout, (Qw.QPushButton("Extra"),), label="Inserted", search_widget=first)

    label_item = layout.itemAt(1, Qw.QFormLayout.ItemRole.LabelRole)
    assert label_item.widget().text() == "Inserted"


def test_insert_helpers_ignore_missing_labels(qapp, qtbot):
    parent = Qw.QWidget()
    layout = Qw.QFormLayout(parent)
    qtbot.addWidget(parent)
    layout.addRow("Existing", Qw.QLineEdit())

    _insert_before_widget(parent, layout, "Missing", None, Qw.QLabel("Before"))
    _insert_after_widget(parent, layout, "Missing", None, Qw.QLabel("After"))

    assert layout.rowCount() == 1
