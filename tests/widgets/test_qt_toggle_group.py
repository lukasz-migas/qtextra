"""Tests for the toggle group widget."""

import pytest

from qtextra.widgets.qt_toggle_group import QtToggleGroup


@pytest.fixture
def toggle_group(qtbot):
    widget = QtToggleGroup(None, options=["Alpha", "Beta", "Gamma"], value="Beta")
    qtbot.addWidget(widget)
    return widget


def test_qt_toggle_group_initial_state(toggle_group):
    assert toggle_group.options == ["Alpha", "Beta", "Gamma"]
    assert toggle_group.value == "Beta"
    assert toggle_group.index == 1
    assert [button.text() for button in toggle_group.checked_buttons] == ["Beta"]


def test_qt_toggle_group_value_setter_and_signals(toggle_group):
    values = []
    indices = []
    toggle_group.evt_changed.connect(values.append)
    toggle_group.evt_index_changed.connect(indices.append)

    toggle_group.value = "Gamma"
    assert toggle_group.value == "Gamma"
    assert toggle_group.index == 2

    toggle_group.buttons[2].click()

    assert values == ["Gamma"]
    assert indices == [2]


def test_qt_toggle_group_non_exclusive_mode(qtbot):
    widget = QtToggleGroup(None, options=["Alpha", "Beta", "Gamma"], value=["Alpha"], exclusive=False)
    qtbot.addWidget(widget)

    assert widget.value == ["Alpha"]
    assert widget.index == [0]

    widget.setValue(["Alpha", "Gamma"])
    assert widget.value == ["Alpha", "Gamma"]
    assert widget.index == [0, 2]


def test_qt_toggle_group_from_schema_uses_defaults_and_enum(qtbot):
    seen = []
    widget = QtToggleGroup.from_schema(
        None,
        options=["Unused"],
        items={"enum": ["One", "Two"]},
        default="Two",
        description="Toggle help",
        func=seen.append,
    )
    qtbot.addWidget(widget)

    assert widget.options == ["One", "Two"]
    assert widget.value == "Two"
    assert widget.toolTip() == ""

    widget.buttons[0].click()
    assert seen == ["One"]
