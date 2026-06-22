"""Tests for the dependency graph widget."""

from __future__ import annotations

from typing import Any

import pytest
from qtpy.QtCore import QPoint, QPointF, Qt
from qtpy.QtGui import QColor, QIcon, QPixmap
from qtpy.QtWidgets import QGraphicsItem

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
    model = DependencyGraphNode(id="model", title="Model", state=TaskState.RUNNING)

    nodes = {node.id: node for node in widget.get_nodes()}

    assert model.state == "running"
    assert nodes["prepare"].state == "finished"
    assert nodes["right"].state == "queued"
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

    assert blocker.args == ["right", "failed"]
    assert widget._node_items["right"] is item
    assert item.pos() == position
    assert item.node.state == "failed"
    assert item.state_color == QColor(STATE_TO_COLOR[TaskState.FAILED])

    with pytest.raises(KeyError, match="unknown"):
        widget.set_node_state("unknown", TaskState.RUNNING)


def test_dependency_graph_supports_arbitrary_states_and_colors(qtbot: Any) -> None:
    widget = QtDependencyGraph(
        [{"id": "task", "title": "Task", "state": "waiting_review"}],
        state_colors={"waiting_review": "#123456", "approved": "#abcdef"},
    )
    qtbot.addWidget(widget)

    assert widget.get_state_colors()["waiting_review"] == QColor("#123456")
    assert widget._node_items["task"].state_color == QColor("#123456")

    widget.set_node_state("task", "approved")

    assert widget._node_items["task"].state_color == QColor("#abcdef")
    assert widget.get_nodes()[0].state == "approved"


def test_dependency_graph_rejects_unconfigured_or_invalid_state_colors(qtbot: Any) -> None:
    widget = QtDependencyGraph(
        [{"id": "task", "title": "Task", "state": "custom"}],
        state_colors={"custom": "#123456"},
    )
    qtbot.addWidget(widget)

    with pytest.raises(ValueError, match="No color configured"):
        widget.set_node_state("task", "missing")
    with pytest.raises(ValueError, match="Missing colors"):
        widget.set_state_colors()
    with pytest.raises(ValueError, match="Invalid color"):
        widget.set_state_colors({"custom": "not-a-color"})

    assert widget.get_nodes()[0].state == "custom"
    assert widget.get_state_colors()["custom"] == QColor("#123456")


def test_dependency_graph_has_colors_for_every_task_state(qtbot: Any) -> None:
    widget = QtDependencyGraph()
    qtbot.addWidget(widget)

    colors = widget.get_state_colors()

    assert set(colors) == {state.value for state in TaskState}
    assert all(color.isValid() for color in colors.values())


@pytest.mark.parametrize(
    ("nodes", "message"),
    [
        ([{"id": "a", "title": "A"}, {"id": "a", "title": "Again"}], "Duplicate"),
        ([{"id": "a", "title": "A", "dependencies": ["missing"]}], "unknown dependencies"),
        ([{"id": "a", "title": "A", "dependencies": ["a"]}], "depend on itself"),
        ([{"id": "a", "title": "A", "state": "custom"}], "No colors configured"),
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


def test_dependency_graph_movement_updates_connected_edges_and_snaps(qtbot: Any) -> None:
    widget = QtDependencyGraph(
        [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B", "dependencies": ["a"]},
            {"id": "c", "title": "C", "dependencies": ["b"]},
        ],
        grid_spacing=20.0,
    )
    qtbot.addWidget(widget)
    item = widget._node_items["b"]
    start = QPointF(item.pos())
    incoming_before = widget._edge_items[("a", "b")].path().boundingRect()
    outgoing_before = widget._edge_items[("b", "c")].path().boundingRect()

    item.setPos(start + QPointF(13.0, 27.0))

    assert widget._edge_items[("a", "b")].path().boundingRect() != incoming_before
    assert widget._edge_items[("b", "c")].path().boundingRect() != outgoing_before

    with qtbot.waitSignal(widget.evt_node_moved, timeout=500) as blocker:
        widget._on_node_drag_finished("b", start)

    expected = QPointF(round((start.x() + 13.0) / 20.0) * 20.0, round((start.y() + 27.0) / 20.0) * 20.0)
    assert item.pos() == expected
    assert blocker.args == ["b", expected]
    assert widget.sceneRect().contains(item.sceneBoundingRect())


def test_dependency_graph_free_drag_and_movement_locking(qtbot: Any) -> None:
    widget = QtDependencyGraph([{"id": "task", "title": "Task"}], snap_to_grid=False)
    widget.resize(600, 400)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    item = widget._node_items["task"]
    start = QPointF(item.pos())
    center = widget.mapFromScene(item.mapToScene(item.card_rect().center()))

    with qtbot.waitSignal(widget.evt_node_moved, timeout=500):
        qtbot.mousePress(widget.viewport(), Qt.MouseButton.LeftButton, pos=center)
        qtbot.mouseMove(widget.viewport(), pos=center + QPoint(40, 20))
        qtbot.mouseRelease(widget.viewport(), Qt.MouseButton.LeftButton, pos=center + QPoint(40, 20))

    assert item.pos() == start + QPointF(40.0, 20.0)
    assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable

    widget.set_nodes_movable(False)

    assert widget.get_nodes_movable() is False
    assert not item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable


def test_dependency_graph_position_api_preserves_and_resets_layout(qtbot: Any) -> None:
    nodes = [
        {"id": "a", "title": "A"},
        {"id": "b", "title": "B", "dependencies": ["a"]},
    ]
    widget = QtDependencyGraph(nodes)
    qtbot.addWidget(widget)
    automatic = widget.get_node_positions()

    widget.set_node_position("a", (123.0, 234.0))
    assert widget.get_node_positions()["a"] == (123.0, 234.0)

    widget.set_nodes(nodes)
    assert widget.get_node_positions()["a"] == (123.0, 234.0)

    before_invalid = widget.get_node_positions()
    with pytest.raises(KeyError, match="missing"):
        widget.set_node_positions({"a": (5.0, 6.0), "missing": (7.0, 8.0)})
    assert widget.get_node_positions() == before_invalid

    widget.reset_layout()
    assert widget.get_node_positions() == automatic

    widget.set_node_position("a", (321.0, 432.0))
    widget.set_orientation("vertical")
    assert widget.get_node_positions()["a"] != (321.0, 432.0)


def test_dependency_graph_supports_icons_and_safe_node_copies(qtbot: Any) -> None:
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("#ff0000"))
    direct_icon = QIcon(pixmap)
    widget = QtDependencyGraph(
        [
            DependencyGraphNode(id="direct", title="Direct", description="Full description", icon=direct_icon),
            {"id": "alias", "title": "Alias", "icon": "graph"},
        ]
    )
    qtbot.addWidget(widget)

    copied_nodes = {node.id: node for node in widget.get_nodes()}

    assert isinstance(copied_nodes["direct"].icon, QIcon)
    assert copied_nodes["direct"].icon is not direct_icon
    assert widget._node_items["direct"]._icon.isNull() is False
    assert widget._node_items["alias"]._icon.isNull() is False
    assert "Full description" in widget._node_items["direct"].toolTip()
    assert "State: queued" in widget._node_items["direct"].toolTip()

    widget.set_node_icon("direct", "info")

    assert widget.get_nodes()[0].icon == "info"
    assert widget._node_items["direct"]._icon.isNull() is False


def test_dependency_graph_grid_configuration_and_zoom_density(qtbot: Any) -> None:
    widget = QtDependencyGraph([{"id": "task", "title": "Task"}])
    qtbot.addWidget(widget)

    assert widget.get_grid_visible() is True
    assert widget.get_snap_to_grid() is True
    assert widget.get_grid_spacing() == 20.0
    assert widget._effective_grid_spacing() == 20.0

    widget.set_zoom_factor(0.1)
    assert widget._effective_grid_spacing() > widget.get_grid_spacing()
    widget.set_grid_spacing(25.0)
    widget.set_grid_visible(False)
    widget.set_snap_to_grid(False)

    assert widget.get_grid_spacing() == 25.0
    assert widget.get_grid_visible() is False
    assert widget.get_snap_to_grid() is False
    with pytest.raises(ValueError, match="positive finite"):
        widget.set_grid_spacing(0.0)


def test_dependency_graph_supports_interactive_pan_and_bounded_zoom(qtbot: Any) -> None:
    widget = QtDependencyGraph([{"id": "task", "title": "Task"}])
    qtbot.addWidget(widget)

    assert widget.dragMode() == widget.DragMode.ScrollHandDrag
    assert widget.zoom_factor() == pytest.approx(1.0)

    with qtbot.waitSignal(widget.evt_zoom_changed, timeout=500) as blocker:
        widget.zoom_in()

    assert blocker.args == [pytest.approx(widget.ZOOM_STEP)]
    assert widget.zoom_factor() == pytest.approx(widget.ZOOM_STEP)

    widget.zoom_out()
    assert widget.zoom_factor() == pytest.approx(1.0)

    widget.set_zoom_factor(100.0)
    assert widget.zoom_factor() == pytest.approx(widget.MAX_ZOOM)
    widget.set_zoom_factor(0.001)
    assert widget.zoom_factor() == pytest.approx(widget.MIN_ZOOM)
    widget.reset_zoom()
    assert widget.zoom_factor() == pytest.approx(1.0)

    with pytest.raises(ValueError, match="positive finite"):
        widget.set_zoom_factor(0.0)


def test_dependency_graph_keyboard_navigation_and_double_click(qtbot: Any) -> None:
    widget = QtDependencyGraph([{"id": "task", "title": "Task"}])
    widget.resize(500, 300)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    qtbot.keyClick(widget, Qt.Key.Key_Plus)
    assert widget.zoom_factor() == pytest.approx(widget.ZOOM_STEP)
    qtbot.keyClick(widget, Qt.Key.Key_Minus)
    assert widget.zoom_factor() == pytest.approx(1.0)
    widget.zoom_in()
    qtbot.keyClick(widget, Qt.Key.Key_0)
    assert widget.zoom_factor() == pytest.approx(1.0)

    position = widget.mapFromScene(
        widget._node_items["task"].mapToScene(widget._node_items["task"].card_rect().center())
    )
    with qtbot.waitSignal(widget.evt_node_double_clicked, timeout=500) as blocker:
        qtbot.mouseDClick(widget.viewport(), Qt.MouseButton.LeftButton, pos=position)

    assert blocker.args == ["task"]


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
