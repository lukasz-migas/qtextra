"""Tests for automatic widget generation helpers."""

from qtpy import QtWidgets as Qw
from superqt import QLabeledDoubleSlider, QLabeledSlider

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
from qtextra.widgets.qt_button_color import QtColorSwatch
from qtextra.widgets.qt_combobox_check import QtCheckableComboBox
from qtextra.widgets.qt_combobox_multi import QtMultiSelectComboBox
from qtextra.widgets.qt_toggle_group import QtToggleGroup


def test_guess_widget_cls_handles_common_schema_shapes():
    assert guess_widget_cls({"type": "string"}) == "line_edit"
    assert guess_widget_cls({"type": "string", "enum": ["A", "B"]}) == "combo_box"
    assert guess_widget_cls({"type": "string", "default": "#112233"}) == "color"
    assert guess_widget_cls({"type": "string", "value": "#112233"}) == "color"
    assert guess_widget_cls({"type": "string", "const": "#112233"}) == "color"
    assert guess_widget_cls({"type": "string", "enum": ["#112233", "#445566"]}) == "combo_box"
    assert guess_widget_cls({"type": "array", "enum": ["A", "B"]}) == "multi_combo_box"
    assert guess_widget_cls({"type": "array", "items": {"enum": ["A", "B"]}}) == "multi_combo_box"
    assert guess_widget_cls({"type": "boolean"}) == "checkbox"
    assert guess_widget_cls({"type": "integer"}) == "int_spin_box"
    assert guess_widget_cls({"type": "number"}) == "double_spin_box"
    assert guess_widget_cls({"anyOf": [{"type": "string"}]}) == "line_edit"
    assert guess_widget_cls({"type": ["null", "string"]}) == "line_edit"
    assert guess_widget_cls({"anyOf": [{"type": "null"}, {"type": "string", "default": "#112233"}]}) == "line_edit"
    assert guess_widget_cls({"type": "string", "format": "textarea"}) == "text_edit"


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


def test_get_widget_for_schema_builds_color_swatch(qapp, qtbot):
    parent = Qw.QWidget()
    qtbot.addWidget(parent)

    widget, layout = get_widget_for_schema(
        parent,
        {
            "type": "string",
            "default": "#112233",
            "description": "Pick a color",
        },
    )

    assert isinstance(widget, QtColorSwatch)
    assert get_value_from_widget(widget).lower() == "#112233"
    assert widget.toolTip() == "Pick a color"
    assert layout is None


def test_get_widget_for_schema_supports_explicit_color_widget(qapp, qtbot):
    parent = Qw.QWidget()
    qtbot.addWidget(parent)

    widget, layout = get_widget_for_schema(parent, {"widget_cls": "color", "value": "#445566"})

    assert isinstance(widget, QtColorSwatch)
    assert get_value_from_widget(widget).lower() == "#445566"
    assert layout is None


def test_get_widget_for_schema_builds_core_helper_widgets(qapp, qtbot):
    parent = Qw.QWidget()
    qtbot.addWidget(parent)

    checkable_combo, _ = get_widget_for_schema(
        parent,
        {"type": "array", "items": {"enum": ["Alpha", "Beta", "Gamma"]}, "value": ["Alpha", "Gamma"]},
    )
    text_edit, _ = get_widget_for_schema(parent, {"widget_cls": "text_edit", "default": "Alpha"})
    label, _ = get_widget_for_schema(parent, {"widget_cls": "label", "value": "Read only"})
    combo, _ = get_widget_for_schema(
        parent, {"widget_cls": "eliding_combo_box", "enum": ["One", "Two"], "value": "Two"}
    )
    slider, _ = get_widget_for_schema(
        parent, {"widget_cls": "slider_with_text", "minimum": 0, "maximum": 10, "value": 4}
    )
    double_slider, _ = get_widget_for_schema(
        parent,
        {
            "widget_cls": "double_slider_with_text",
            "minimum": 0,
            "maximum": 1,
            "value": 0.5,
            "n_decimals": 2,
        },
    )
    multi_combo, _ = get_widget_for_schema(
        parent,
        {
            "widget_cls": "multi_select_combo_box",
            "items": {"enum": ["One", "Two", "Three"]},
            "value": ["One", "Three"],
        },
    )

    assert isinstance(checkable_combo, QtCheckableComboBox)
    assert get_value_from_widget(checkable_combo) == ["Alpha", "Gamma"]
    assert isinstance(text_edit, Qw.QTextEdit)
    assert get_value_from_widget(text_edit) == "Alpha"
    assert isinstance(label, Qw.QLabel)
    assert get_value_from_widget(label) == "Read only"
    assert isinstance(combo, Qw.QComboBox)
    assert get_value_from_widget(combo) == "Two"
    assert isinstance(slider, QLabeledSlider)
    assert get_value_from_widget(slider) == 4
    assert isinstance(double_slider, QLabeledDoubleSlider)
    assert get_value_from_widget(double_slider) == 0.5
    assert isinstance(multi_combo, QtMultiSelectComboBox)
    assert get_value_from_widget(multi_combo) == ["One", "Three"]


def test_get_and_set_value_for_supported_widgets(qapp, qtbot):
    line_edit = Qw.QLineEdit()
    text_edit = Qw.QTextEdit()
    label = Qw.QLabel()
    checkbox = Qw.QCheckBox()
    spinbox = Qw.QSpinBox()
    checkable_combo = QtCheckableComboBox()
    checkable_combo.addItems(["Alpha", "Beta"])
    combo = Qw.QComboBox()
    combo.addItems(["None", "Alpha", "Beta"])
    swatch = QtColorSwatch(initial_color="#112233")
    multi_combo = QtMultiSelectComboBox(["One", "Two", "Three"])
    toggle = QtToggleGroup(None, options=["Red", "Blue"], value="Red")
    qtbot.addWidget(toggle)
    qtbot.addWidget(swatch)
    qtbot.addWidget(multi_combo)

    set_value_to_widget(line_edit, ["A", "B"])
    set_value_to_widget(text_edit, "Long text")
    set_value_to_widget(label, None)
    set_value_to_widget(checkbox, 1)
    set_value_to_widget(spinbox, 5)
    set_value_to_widget(checkable_combo, ["Alpha", "Beta"])
    set_value_to_widget(combo, "")
    set_value_to_widget(swatch, "#445566")
    set_value_to_widget(multi_combo, "One;Three")
    set_value_to_widget(toggle, "Blue")

    assert get_value_from_widget(line_edit) == "A,B"
    assert get_value_from_widget(text_edit) == "Long text"
    assert get_value_from_widget(label) == ""
    assert get_value_from_widget(checkbox) is True
    assert get_value_from_widget(spinbox) == 5
    assert get_value_from_widget(checkable_combo) == ["Alpha", "Beta"]
    assert get_value_from_widget(combo) == "None"
    assert get_value_from_widget(swatch).lower() == "#445566"
    assert get_value_from_widget(multi_combo) == ["One", "Three"]
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
