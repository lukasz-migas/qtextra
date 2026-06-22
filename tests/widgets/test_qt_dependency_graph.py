"""Tests for the dependency graph widget."""

from __future__ import annotations

from typing import Any

import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

from qtextra.config import THEMES
from qtextra.queue._constants import STATE_TO_COLOR
from qtextra.typing import TaskState
from qtextra.widgets.qt_dependency_graph import DependencyGraphNode, QtDependencyGraph


def _graph_nodes() -> list[dict[str, object]]:
    return [
        {"id": "prepare", "title": "Prepare", "description": "Prepare inputs", "state": "finished"},
        {"id": "left", "title": "Left branch", "dependencies": ["prepare"], "state": "running"},
        {"id": "right", "title": "Right branch", "dependencies": ["prepare"]},
        {"id": "publish", "title": "Publish", "dependencies": ["left", "right"]},
        {"id": "independent", "title": "Independent"},
    ]


def test_dependency_graph_node_defaults_and_dictionary_coercion(qtbot: Any) -> None:
    widget = QtDependencyGraph(_graph_nodes())
    qtbot.addWidget(widget)

    nodes = {node.id: node for node in widget.get_nodes()}

    assert nodes["prepare"].state == TaskState.FINISHED
    assert nodes["right"].state == TaskState.QUEUED
    assert nodes["left"].dependencies == ("prepare",)


def test_dependency_graph_derives_ports_and_branching_edges(qtbot: Any) -> None:
    widget = QtDependencyGraph(_graph_nodes())
    qtbot.addWidget(widget)

    assert widget._node_items["prepare"].has_input is False
    assert widget._node_items["prepare"].has_output is True
    assert widget._node_items["publish"].has_input is True
    assert widget._node_items["publish"].has_output is False
    assert widget._node_items["independent"].has_input is False
    assert widget._node_items["independent"].has_output is False
    assert set(widget._edge_items) == {
        ("prepare", "left"),
        ("prepare", "right"),
        ("left", "publish"),
        ("right", "publish"),
    }


def test_dependency_graph_layout_flows_in_both_orientations(qtbot: Any) -> None:
    widget = QtDependencyGraph(_graph_nodes(), orientation="horizontal")
    qtbot.addWidget(widget)

    assert widget._node_items["prepare"].x() < widget._node_items["left"].x()
    assert widget._node_items["left"].x() < widget._node_items["publish"].x()

    widget.set_orientation(Qt.Orientation.Vertical)

    assert widget.get_orientation() == "vertical"
    assert widget._node_items["prepare"].y() < widget._node_items["left"].y()
    assert widget._node_items["left"].y() < widget._node_items["publish"].y()


def test_dependency_graph_highlights_transitive_relations(qtbot: Any) -> None:
    nodes = [
        {"id": "a", "title": "A"},
        {"id": "b", "title": "B", "dependencies": ["a"]},
        {"id": "c", "title": "C", "dependencies": ["b"]},
        {"id": "d", "title": "D", "dependencies": ["c"]},
        {"id": "other", "title": "Other"},
    ]
    widget = QtDependencyGraph(nodes)
    qtbot.addWidget(widget)
    state_color = QColor(widget._node_items["a"].state_color)

    widget.select_node("c")

    assert widget.selected_node_id() == "c"
    assert widget._node_items["a"].relation == "upstream"
    assert widget._node_items["b"].relation == "upstream"
    assert widget._node_items["c"].relation == "selected"
    assert widget._node_items["d"].relation == "downstream"
    assert widget._node_items["other"].relation == "unrelated"
    assert widget._node_items["other"].opacity() < 1.0
    assert widget._node_items["a"].state_color == state_color
    assert widget._edge_items[("a", "b")].relation == "upstream"
    assert widget._edge_items[("c", "d")].relation == "downstream"

    widget.select_node(None)

    assert all(item.relation == "normal" for item in widget._node_items.values())


def test_dependency_graph_click_emits_signals(qtbot: Any) -> None:
    widget = QtDependencyGraph([{"id": "task", "title": "Task"}])
    widget.resize(500, 300)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    position = widget.mapFromScene(widget._node_items["task"].card_rect().center())

    with (
        qtbot.waitSignal(widget.evt_node_clicked, timeout=500) as click_blocker,
        qtbot.waitSignal(widget.evt_selection_changed, timeout=500) as selection_blocker,
    ):
        qtbot.mouseClick(widget.viewport(), Qt.MouseButton.LeftButton, pos=position)

    assert click_blocker.args == ["task"]
    assert selection_blocker.args == ["task"]


def test_dependency_graph_set_node_state_updates_without_relayout(qtbot: Any) -> None:
    widget = QtDependencyGraph(_graph_nodes())
    qtbot.addWidget(widget)
    item = widget._node_items["right"]
    position = item.pos()

    with qtbot.waitSignal(widget.evt_node_state_changed, timeout=500) as blocker:
        widget.set_node_state("right", TaskState.FAILED)

    assert blocker.args == ["right", TaskState.FAILED]
    assert widget._node_items["right"] is item
    assert item.pos() == position
    assert item.node.state == TaskState.FAILED
    assert item.state_color == QColor(STATE_TO_COLOR[TaskState.FAILED])

    with pytest.raises(KeyError, match="unknown"):
        widget.set_node_state("unknown", TaskState.RUNNING)


def test_dependency_graph_supports_state_color_overrides(qtbot: Any) -> None:
    widget = QtDependencyGraph(
        [{"id": "task", "title": "Task"}],
        state_colors={TaskState.QUEUED: "#123456"},
    )
    qtbot.addWidget(widget)

    assert widget.get_state_colors()[TaskState.QUEUED] == QColor("#123456")
    assert widget._node_items["task"].state_color == QColor("#123456")

    widget.set_state_colors({"finished": "#abcdef"})
    widget.set_node_state("task", TaskState.FINISHED)

    assert widget._node_items["task"].state_color == QColor("#abcdef")


def test_dependency_graph_has_colors_for_every_task_state(qtbot: Any) -> None:
    widget = QtDependencyGraph()
    qtbot.addWidget(widget)

    colors = widget.get_state_colors()

    assert set(colors) == set(TaskState)
    assert all(color.isValid() for color in colors.values())


@pytest.mark.parametrize(
    ("nodes", "message"),
    [
        ([{"id": "a", "title": "A"}, {"id": "a", "title": "Again"}], "Duplicate"),
        ([{"id": "a", "title": "A", "dependencies": ["missing"]}], "unknown dependencies"),
        ([{"id": "a", "title": "A", "dependencies": ["a"]}], "depend on itself"),
        (
            [
                {"id": "a", "title": "A", "dependencies": ["b"]},
                {"id": "b", "title": "B", "dependencies": ["a"]},
            ],
            "cycle",
        ),
    ],
)
def test_dependency_graph_rejects_invalid_data_atomically(
    qtbot: Any,
    nodes: list[dict[str, object]],
    message: str,
) -> None:
    widget = QtDependencyGraph([{"id": "existing", "title": "Existing"}])
    qtbot.addWidget(widget)

    with pytest.raises(ValueError, match=message):
        widget.set_nodes(nodes)

    assert [node.id for node in widget.get_nodes()] == ["existing"]
    assert set(widget._node_items) == {"existing"}


def test_dependency_graph_navigation_and_rendering(qtbot: Any) -> None:
    nodes = [DependencyGraphNode(id=f"task-{index}", title=f"Task {index}") for index in range(8)]
    for index in range(1, len(nodes)):
        nodes[index].dependencies = (nodes[index - 1].id,)
    widget = QtDependencyGraph(nodes)
    widget.resize(320, 220)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    assert widget.sceneRect().width() > widget.viewport().width()
    widget.center_on_node("task-7")
    widget.fit_to_view()

    assert widget.grab().isNull() is False


def test_dependency_graph_repaints_after_theme_change(qtbot: Any) -> None:
    widget = QtDependencyGraph([{"id": "task", "title": "Task"}])
    qtbot.addWidget(widget)
    original_theme = THEMES.theme
    next_theme = "dark" if original_theme != "dark" else "light"

    try:
        THEMES.theme = next_theme

        assert widget.backgroundBrush().color() == THEMES.get_qt_color("background")
        assert widget._node_items["task"].state_color == QColor(STATE_TO_COLOR[TaskState.QUEUED])
    finally:
        THEMES.theme = original_theme
