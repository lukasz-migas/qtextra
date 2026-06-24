"""Scrollable dependency graph widget for stateful tasks."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from math import ceil, floor, isfinite
from typing import Callable, ClassVar

from qtpy.QtCore import Property, QPointF, QRectF, Qt, Signal
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from qtpy.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
    QStyleOptionGraphicsItem,
    QWidget,
)

from qtextra._pydantic_compat import BaseModel
from qtextra.config import THEMES
from qtextra.queue._constants import STATE_TO_COLOR
from qtextra.typing import Orientation, TaskState
from qtextra.utils.color import get_text_color

__all__ = ["DependencyGraphNode", "QtDependencyGraph"]


class DependencyGraphNode(BaseModel):
    """Declarative data for one task in a dependency graph."""

    id: str
    title: str
    description: str = ""
    dependencies: tuple[str, ...] = ()
    state: str = TaskState.QUEUED.value
    icon: QIcon | str | None = None
    group: str | None = None

    class Config:
        """Allow Qt icon values in the declarative node model."""

        arbitrary_types_allowed = True


class _DependencyNodeItem(QGraphicsObject):
    """Paint one task card and its derived connection ports."""

    WIDTH: ClassVar[float] = 300.0
    MIN_HEIGHT: ClassVar[float] = 112.0
    PADDING: ClassVar[float] = 14.0
    ACCENT_WIDTH: ClassVar[float] = 6.0
    PORT_RADIUS: ClassVar[float] = 5.0
    TITLE_GAP: ClassVar[float] = 8.0
    DESCRIPTION_GAP: ClassVar[float] = 10.0
    ICON_SIZE: ClassVar[float] = 22.0
    ICON_GAP: ClassVar[float] = 8.0

    def __init__(
        self,
        node: DependencyGraphNode,
        orientation: Orientation,
        state_color: QColor,
        has_input: bool,
        has_output: bool,
        icon_resolver: Callable[[QIcon | str | None], QIcon | None],
        position_changed: Callable[[str], None],
        drag_finished: Callable[[str, QPointF], None],
        movable: bool,
    ) -> None:
        """Initialize a task card."""
        super().__init__()
        self.node = node
        self.orientation = orientation
        self.state_color = QColor(state_color)
        self.has_input = has_input
        self.has_output = has_output
        self._icon_resolver = icon_resolver
        self._position_changed = position_changed
        self._drag_finished = drag_finished
        self._icon = self._icon_resolver(node.icon)
        self._drag_start_position: QPointF | None = None
        self.relation = "normal"
        self._title_font = QFont()
        self._title_font.setBold(True)
        self._state_font = QFont()
        self._state_font.setPointSizeF(max(7.0, self._state_font.pointSizeF() - 1.0))
        self._description_font = QFont()
        self._height = self.MIN_HEIGHT
        self._update_height()
        self._update_tooltip()
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.set_movable(movable)
        self.setZValue(1.0)

    def boundingRect(self) -> QRectF:
        """Return the task card bounds, including its ports."""
        margin = self.PORT_RADIUS + 2.0
        return QRectF(0.0, 0.0, self.WIDTH, self._height).adjusted(-margin, -margin, margin, margin)

    def card_rect(self) -> QRectF:
        """Return the rectangular task-card body."""
        return QRectF(0.0, 0.0, self.WIDTH, self._height)

    def input_anchor(self) -> QPointF:
        """Return the scene position of the input port."""
        rect = self.card_rect()
        point = QPointF(rect.left(), rect.center().y())
        if self.orientation == "vertical":
            point = QPointF(rect.center().x(), rect.top())
        return self.mapToScene(point)

    def output_anchor(self) -> QPointF:
        """Return the scene position of the output port."""
        rect = self.card_rect()
        point = QPointF(rect.right(), rect.center().y())
        if self.orientation == "vertical":
            point = QPointF(rect.center().x(), rect.bottom())
        return self.mapToScene(point)

    def set_relation(self, relation: str) -> None:
        """Set the relationship highlight applied to this node."""
        self.relation = relation
        self.setOpacity(0.28 if relation == "unrelated" else 1.0)
        if self._drag_start_position is None:
            self.setZValue(2.0 if relation == "selected" else 1.0)
        self.update()

    def set_state(self, state: str, color: QColor) -> None:
        """Update state data and repaint without changing graph geometry."""
        self.node.state = state
        self.state_color = QColor(color)
        self._update_tooltip()
        self.update()

    def set_icon(self, icon: QIcon | str | None) -> None:
        """Update the node icon and repaint the card."""
        self.node.icon = QIcon(icon) if isinstance(icon, QIcon) else icon
        self._icon = self._icon_resolver(self.node.icon)
        self.update()

    def set_movable(self, movable: bool) -> None:
        """Enable or disable direct node dragging."""
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)

    def refresh_theme(self) -> None:
        """Repaint the node using the active application theme."""
        if isinstance(self.node.icon, str):
            self._icon = self._icon_resolver(self.node.icon)
        self.update()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: object) -> object:
        """Notify the graph when this node moves."""
        result = super().itemChange(change, value)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene() is not None:
            self._position_changed(self.node.id)
        return result

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Remember the initial position for final movement notification."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = QPointF(self.pos())
            self.setZValue(3.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Finalize a node drag and restore normal stacking."""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start_position is not None:
            self._drag_finished(self.node.id, self._drag_start_position)
            self._drag_start_position = None
        self.setZValue(2.0 if self.relation == "selected" else 1.0)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Paint the card, labels, accent, and ports."""
        del option, widget
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        card = self.card_rect()
        border_color, border_width = self._border_style()
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush(THEMES.get_qt_color("canvas")))
        painter.drawRoundedRect(card, 7.0, 7.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.state_color))
        accent = QRectF(card.left(), card.top(), self.ACCENT_WIDTH, card.height())
        painter.drawRoundedRect(accent, 3.0, 3.0)

        content_left = self.PADDING + self.ACCENT_WIDTH
        content_width = card.width() - content_left - self.PADDING
        state_text = self.node.state.replace("-", " ").replace("_", " ").title()
        state_metrics = QFontMetricsF(self._state_font)
        state_width = state_metrics.horizontalAdvance(state_text) + 14.0
        state_height = state_metrics.height() + 6.0
        state_rect = QRectF(card.right() - self.PADDING - state_width, self.PADDING, state_width, state_height)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.state_color))
        painter.drawRoundedRect(state_rect, state_height / 2.0, state_height / 2.0)
        painter.setFont(self._state_font)
        painter.setPen(get_text_color(self.state_color))
        painter.drawText(state_rect, Qt.AlignmentFlag.AlignCenter, state_text)

        title_left = content_left
        if self._icon is not None:
            icon_rect = QRectF(
                content_left,
                self.PADDING + (state_height - self.ICON_SIZE) / 2.0,
                self.ICON_SIZE,
                self.ICON_SIZE,
            )
            self._icon.paint(painter, icon_rect.toRect(), Qt.AlignmentFlag.AlignCenter)
            title_left = icon_rect.right() + self.ICON_GAP
        title_width = max(20.0, card.right() - self.PADDING - state_width - self.TITLE_GAP - title_left)
        title_rect = QRectF(title_left, self.PADDING, title_width, state_height)
        painter.setFont(self._title_font)
        painter.setPen(THEMES.get_qt_color("text"))
        title = QFontMetricsF(self._title_font).elidedText(
            self.node.title,
            Qt.TextElideMode.ElideRight,
            title_width,
        )
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

        description_top = self.PADDING + state_height + self.DESCRIPTION_GAP
        description_rect = QRectF(
            content_left,
            description_top,
            content_width,
            card.bottom() - self.PADDING - description_top,
        )
        painter.setFont(self._description_font)
        painter.setPen(THEMES.get_qt_color("text"))
        painter.drawText(
            description_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            self.node.description,
        )

        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(QBrush(THEMES.get_qt_color("canvas")))
        if self.has_input:
            painter.drawEllipse(self.mapFromScene(self.input_anchor()), self.PORT_RADIUS, self.PORT_RADIUS)
        if self.has_output:
            painter.drawEllipse(self.mapFromScene(self.output_anchor()), self.PORT_RADIUS, self.PORT_RADIUS)

    def _update_height(self) -> None:
        metrics = QFontMetricsF(self._description_font)
        width = self.WIDTH - (2.0 * self.PADDING) - self.ACCENT_WIDTH
        bounds = metrics.boundingRect(
            QRectF(0.0, 0.0, width, 10000.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            self.node.description,
        )
        title_height = max(QFontMetricsF(self._title_font).height(), QFontMetricsF(self._state_font).height() + 6.0)
        content_height = 2.0 * self.PADDING + title_height + self.DESCRIPTION_GAP + bounds.height()
        self._height = max(self.MIN_HEIGHT, content_height)

    def _border_style(self) -> tuple[QColor, float]:
        if self.relation == "selected":
            return THEMES.get_qt_color("highlight"), 3.0
        if self.relation == "upstream":
            return THEMES.get_qt_color("info"), 2.5
        if self.relation == "downstream":
            return THEMES.get_qt_color("secondary"), 2.5
        return THEMES.get_qt_color("primary"), 1.5

    def _update_tooltip(self) -> None:
        lines = [self.node.title]
        if self.node.description:
            lines.append(self.node.description)
        lines.append(f"State: {self.node.state}")
        self.setToolTip("\n".join(lines))


class _DependencyEdgeItem(QGraphicsPathItem):
    """Draw a directed connector between two task cards."""

    ARROW_SIZE: ClassVar[float] = 8.0

    def __init__(
        self,
        source: _DependencyNodeItem,
        target: _DependencyNodeItem,
        orientation: Orientation,
    ) -> None:
        """Initialize a dependency connector."""
        super().__init__()
        self.source = source
        self.target = target
        self.orientation = orientation
        self.relation = "normal"
        self._arrow = QPolygonF()
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setZValue(-1.0)
        self.update_path()
        self.set_relation("normal")

    def boundingRect(self) -> QRectF:
        """Return bounds that include the connector arrowhead."""
        rect = super().boundingRect()
        if not self._arrow.isEmpty():
            rect = rect.united(self._arrow.boundingRect())
        return rect.adjusted(-2.0, -2.0, 2.0, 2.0)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Paint the connector and arrowhead."""
        super().paint(painter, option, widget)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.pen().color())
        painter.drawPolygon(self._arrow)

    def update_path(self) -> None:
        """Recalculate the connector path from current node positions."""
        self.prepareGeometryChange()
        start = self.source.output_anchor()
        end = self.target.input_anchor()
        path = QPainterPath(start)
        if self.orientation == "horizontal":
            offset = max(40.0, (end.x() - start.x()) * 0.45)
            path.cubicTo(start + QPointF(offset, 0.0), end - QPointF(offset, 0.0), end)
            self._arrow = QPolygonF(
                [
                    end,
                    end + QPointF(-self.ARROW_SIZE, -self.ARROW_SIZE / 2.0),
                    end + QPointF(-self.ARROW_SIZE, self.ARROW_SIZE / 2.0),
                ]
            )
        else:
            offset = max(40.0, (end.y() - start.y()) * 0.45)
            path.cubicTo(start + QPointF(0.0, offset), end - QPointF(0.0, offset), end)
            self._arrow = QPolygonF(
                [
                    end,
                    end + QPointF(-self.ARROW_SIZE / 2.0, -self.ARROW_SIZE),
                    end + QPointF(self.ARROW_SIZE / 2.0, -self.ARROW_SIZE),
                ]
            )
        self.setPath(path)

    def set_relation(self, relation: str) -> None:
        """Set the relationship highlight applied to this connector."""
        self.relation = relation
        if relation == "upstream":
            color, width, opacity = THEMES.get_qt_color("info"), 2.5, 1.0
        elif relation == "downstream":
            color, width, opacity = THEMES.get_qt_color("secondary"), 2.5, 1.0
        else:
            color, width = THEMES.get_qt_color("primary"), 1.5
            opacity = 0.16 if relation == "unrelated" else 0.75
        self.setPen(QPen(color, width))
        self.setOpacity(opacity)
        self.update()


class QtDependencyGraph(QGraphicsView):
    """Display a stateful directed acyclic task graph on a scrollable canvas."""

    evt_node_clicked = Signal(str)
    evt_node_double_clicked = Signal(str)
    evt_group_clicked = Signal(str)
    evt_group_double_clicked = Signal(str)
    evt_selection_changed = Signal(object)
    evt_node_state_changed = Signal(str, object)
    evt_node_moved = Signal(str, QPointF)
    evt_zoom_changed = Signal(float)

    LAYER_SPACING: ClassVar[float] = 110.0
    NODE_SPACING: ClassVar[float] = 42.0
    SCENE_MARGIN: ClassVar[float] = 40.0
    ZOOM_STEP: ClassVar[float] = 1.2
    MIN_ZOOM: ClassVar[float] = 0.1
    MAX_ZOOM: ClassVar[float] = 4.0
    MIN_GRID_SCREEN_SPACING: ClassVar[float] = 8.0
    GROUP_ID_PREFIX: ClassVar[str] = "__group__:"

    def __init__(
        self,
        nodes: Sequence[DependencyGraphNode | Mapping[str, object]] | None = None,
        orientation: Orientation | Qt.Orientation = "horizontal",
        state_colors: Mapping[str | TaskState, QColor | str] | None = None,
        parent: QWidget | None = None,
        *,
        nodes_movable: bool = True,
        grid_visible: bool = True,
        snap_to_grid: bool = True,
        grid_spacing: float = 20.0,
    ) -> None:
        """Initialize the graph view with optional node data."""
        self._scene = QGraphicsScene()
        super().__init__(self._scene, parent)
        self._orientation = self._normalize_orientation(orientation)
        self._nodes: list[DependencyGraphNode] = []
        self._nodes_by_id: dict[str, DependencyGraphNode] = {}
        self._dependencies: dict[str, tuple[str, ...]] = {}
        self._dependants: dict[str, list[str]] = {}
        self._groups: dict[str, tuple[str, ...]] = {}
        self._group_collapsed: dict[str, bool] = {}
        self._visible_nodes: list[DependencyGraphNode] = []
        self._visible_dependencies: dict[str, tuple[str, ...]] = {}
        self._visible_dependants: dict[str, list[str]] = {}
        self._visible_to_group: dict[str, str] = {}
        self._node_to_visible_id: dict[str, str] = {}
        self._node_items: dict[str, _DependencyNodeItem] = {}
        self._edge_items: dict[tuple[str, str], _DependencyEdgeItem] = {}
        self._edges_by_node: dict[str, list[_DependencyEdgeItem]] = {}
        self._selected_node_id: str | None = None
        self._selected_visible_id: str | None = None
        self._state_colors: dict[str, QColor] = {}
        self._node_positions: dict[str, tuple[float, float]] = {}
        self._group_positions: dict[str, tuple[float, float]] = {}
        self._manual_node_positions: set[str] = set()
        self._manual_group_positions: set[str] = set()
        self._nodes_movable = bool(nodes_movable)
        self._grid_visible = bool(grid_visible)
        self._snap_to_grid = bool(snap_to_grid)
        self._grid_spacing = self._validate_grid_spacing(grid_spacing)
        self._updating_scene_rect = False
        self._rebuilding_scene = False

        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.set_state_colors(state_colors)
        THEMES.evt_theme_changed.connect(self._apply_theme)
        self._apply_theme()
        if nodes is not None:
            self.set_nodes(nodes)

    def get_nodes(self) -> list[DependencyGraphNode]:
        """Return deep copies of the configured graph nodes."""
        return [self._copy_node(node) for node in self._nodes]

    def set_nodes(self, nodes: Sequence[DependencyGraphNode | Mapping[str, object]]) -> None:
        """Validate and replace all task nodes, leaving the old graph intact on failure."""
        validated, dependants = self._validate_nodes(nodes)
        previous_selection = self._selected_node_id
        previous_positions = self.get_node_positions()
        previous_group_positions = dict(self._group_positions)
        self._nodes = validated
        self._nodes_by_id = {node.id: node for node in validated}
        self._dependencies = {node.id: node.dependencies for node in validated}
        self._dependants = dependants
        self._refresh_groups()
        self._group_positions = {
            group: position for group, position in previous_group_positions.items() if group in self._groups
        }
        self._manual_node_positions = {
            node_id for node_id in self._manual_node_positions if node_id in self._nodes_by_id
        }
        self._manual_group_positions = {
            group_id for group_id in self._manual_group_positions if group_id in self._groups
        }
        self._selected_node_id = None
        self._selected_visible_id = None
        self._rebuild_scene(previous_positions)
        if previous_selection is not None:
            self.evt_selection_changed.emit(None)

    def clear(self) -> None:
        """Remove every node, edge, and active selection from the graph."""
        self.set_nodes([])

    def get_nodes_movable(self) -> bool:
        """Return whether users can drag graph nodes."""
        return self._nodes_movable

    def set_nodes_movable(self, movable: bool) -> None:
        """Enable or disable direct dragging for all graph nodes."""
        self._nodes_movable = bool(movable)
        for item in self._node_items.values():
            item.set_movable(self._nodes_movable)

    nodes_movable = Property(bool, fget=get_nodes_movable, fset=set_nodes_movable)

    def get_grid_visible(self) -> bool:
        """Return whether the dotted canvas grid is visible."""
        return self._grid_visible

    def set_grid_visible(self, visible: bool) -> None:
        """Show or hide the dotted canvas grid."""
        self._grid_visible = bool(visible)
        self.viewport().update()

    grid_visible = Property(bool, fget=get_grid_visible, fset=set_grid_visible)

    def get_snap_to_grid(self) -> bool:
        """Return whether dragged nodes snap to the grid on release."""
        return self._snap_to_grid

    def set_snap_to_grid(self, enabled: bool) -> None:
        """Enable or disable grid snapping after node drags."""
        self._snap_to_grid = bool(enabled)

    snap_to_grid = Property(bool, fget=get_snap_to_grid, fset=set_snap_to_grid)

    def get_grid_spacing(self) -> float:
        """Return the grid spacing in scene pixels."""
        return self._grid_spacing

    def set_grid_spacing(self, spacing: float) -> None:
        """Set the grid spacing used for dots and future snapping."""
        self._grid_spacing = self._validate_grid_spacing(spacing)
        self.viewport().update()

    grid_spacing = Property(float, fget=get_grid_spacing, fset=set_grid_spacing)

    def get_node_positions(self) -> dict[str, tuple[float, float]]:
        """Return serializable scene positions keyed by node ID."""
        self._remember_visible_positions()
        return {
            node_id: self._node_positions[node_id] for node_id in self._nodes_by_id if node_id in self._node_positions
        }

    def set_node_position(self, node_id: str, position: QPointF | tuple[float, float]) -> None:
        """Set one node position and emit its final movement signal."""
        self.set_node_positions({node_id: position})

    def set_node_positions(self, positions: Mapping[str, QPointF | tuple[float, float]]) -> None:
        """Atomically validate and apply one or more node positions."""
        unknown = set(positions).difference(self._nodes_by_id)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise KeyError(f"Unknown dependency graph nodes: {names}")
        normalized = {node_id: self._normalize_position(position) for node_id, position in positions.items()}
        changed: list[tuple[str, QPointF]] = []
        for node_id, position in normalized.items():
            previous = self._node_positions.get(node_id)
            if previous != (position.x(), position.y()):
                self._node_positions[node_id] = (position.x(), position.y())
                self._manual_node_positions.add(node_id)
                changed.append((node_id, QPointF(position)))
            if node_id in self._node_items and self._node_items[node_id].pos() != position:
                self._node_items[node_id].setPos(position)
        self._update_all_edges()
        self._update_scene_rect()
        for node_id, position in changed:
            self.evt_node_moved.emit(node_id, position)

    def reset_layout(self) -> None:
        """Restore the automatic topological layout for all nodes."""
        if not self._node_items:
            return
        self._node_positions.clear()
        self._group_positions.clear()
        self._manual_node_positions.clear()
        self._manual_group_positions.clear()
        self._layout_nodes()
        self._remember_visible_positions()
        self._update_all_edges()
        self._update_scene_rect()

    def set_node_icon(self, node_id: str, icon: QIcon | str | None) -> None:
        """Update the optional icon rendered by one graph node."""
        if node_id not in self._nodes_by_id:
            raise KeyError(f"Unknown dependency graph node: {node_id}")
        icon_value = self._copy_icon(icon)
        self._resolve_icon(icon_value)
        self._nodes_by_id[node_id].icon = icon_value
        if node_id in self._node_items:
            self._node_items[node_id].set_icon(icon_value)

    def get_orientation(self) -> Orientation:
        """Return the current graph flow direction."""
        return self._orientation

    def set_orientation(self, orientation: Orientation | Qt.Orientation) -> None:
        """Set the graph flow direction and rebuild its layout."""
        normalized = self._normalize_orientation(orientation)
        if normalized == self._orientation:
            return
        selected = self._selected_node_id
        self._orientation = normalized
        self._node_positions.clear()
        self._group_positions.clear()
        self._manual_node_positions.clear()
        self._manual_group_positions.clear()
        self._rebuild_scene()
        if selected is not None:
            self.select_node(selected)

    orientation = Property(str, fget=get_orientation, fset=set_orientation)

    def get_state_colors(self) -> dict[str, QColor]:
        """Return copies of the effective state colors, keyed by state name."""
        return {state: QColor(color) for state, color in self._state_colors.items()}

    def set_state_colors(self, colors: Mapping[str | TaskState, QColor | str] | None = None) -> None:
        """Reset built-in colors and apply arbitrary state-color definitions."""
        state_colors = {state.value: QColor(color) for state, color in STATE_TO_COLOR.items()}
        for state, color_value in (colors or {}).items():
            state_name = self._normalize_state(state)
            color = QColor(color_value)
            if not color.isValid():
                raise ValueError(f"Invalid color for node state '{state_name}': {color_value}")
            state_colors[state_name] = color
        missing = {node.state for node in self._nodes}.difference(state_colors)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Missing colors for node states: {names}")
        self._state_colors = state_colors
        for node_id, item in self._node_items.items():
            if node_id in self._nodes_by_id:
                item.set_state(item.node.state, self._state_color(self._nodes_by_id[node_id].state))
            elif node_id in self._visible_to_group:
                item.set_state(item.node.state, self._group_state_color(self._visible_to_group[node_id]))

    def set_node_state(self, node_id: str, state: str | TaskState) -> None:
        """Update one node state without rebuilding or repositioning the graph."""
        if node_id not in self._nodes_by_id:
            raise KeyError(f"Unknown dependency graph node: {node_id}")
        state_name = self._normalize_state(state)
        if state_name not in self._state_colors:
            raise ValueError(f"No color configured for node state: {state_name}")
        self._nodes_by_id[node_id].state = state_name
        visible_id = self._node_to_visible_id.get(node_id, node_id)
        if visible_id == node_id and node_id in self._node_items:
            self._node_items[node_id].set_state(state_name, self._state_color(state_name))
        elif visible_id in self._visible_to_group:
            self._remember_visible_positions()
            self._rebuild_scene(self._node_positions)
        self.evt_node_state_changed.emit(node_id, state_name)

    def selected_node_id(self) -> str | None:
        """Return the selected node ID, or ``None`` when nothing is selected."""
        return self._selected_node_id

    def select_node(self, node_id: str | None) -> None:
        """Select a node and highlight its transitive graph relationships."""
        if node_id is not None and node_id not in self._nodes_by_id:
            raise KeyError(f"Unknown dependency graph node: {node_id}")
        changed = node_id != self._selected_node_id
        self._selected_node_id = node_id
        self._selected_visible_id = None if node_id is None else self._node_to_visible_id.get(node_id, node_id)
        self._update_highlights()
        if changed:
            self.evt_selection_changed.emit(node_id)

    def center_on_node(self, node_id: str) -> None:
        """Center the viewport on a graph node."""
        visible_id = self._node_to_visible_id.get(node_id, node_id)
        if visible_id not in self._node_items:
            raise KeyError(f"Unknown dependency graph node: {node_id}")
        self.centerOn(self._node_items[visible_id])

    def set_group_collapsed(self, group_id: str, collapsed: bool) -> None:
        """Collapse or expand a configured dependency graph group."""
        group_id = self._normalize_group_id(group_id, allow_empty=False)
        if group_id not in self._groups:
            raise KeyError(f"Unknown dependency graph group: {group_id}")
        collapsed = bool(collapsed)
        if self._group_collapsed.get(group_id, True) == collapsed:
            return
        self._remember_visible_positions()
        self._group_collapsed[group_id] = collapsed
        self._rebuild_scene(self._manual_visible_positions())

    def is_group_collapsed(self, group_id: str) -> bool:
        """Return whether a configured dependency graph group is collapsed."""
        group_id = self._normalize_group_id(group_id, allow_empty=False)
        if group_id not in self._groups:
            raise KeyError(f"Unknown dependency graph group: {group_id}")
        return self._group_collapsed.get(group_id, True)

    def get_group_nodes(self, group_id: str) -> list[DependencyGraphNode]:
        """Return deep copies of nodes that belong to a dependency graph group."""
        group_id = self._normalize_group_id(group_id, allow_empty=False)
        if group_id not in self._groups:
            raise KeyError(f"Unknown dependency graph group: {group_id}")
        return [self._copy_node(self._nodes_by_id[node_id]) for node_id in self._groups[group_id]]

    def fit_to_view(self) -> None:
        """Scale the complete graph to fit inside the viewport."""
        if self._node_items:
            previous_zoom = self.zoom_factor()
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._emit_zoom_changed(previous_zoom)

    def zoom_factor(self) -> float:
        """Return the current canvas scale factor."""
        return self.transform().m11()

    def set_zoom_factor(self, factor: float) -> None:
        """Set the canvas scale factor within the supported zoom range."""
        factor = float(factor)
        if not isfinite(factor) or factor <= 0.0:
            raise ValueError(f"Zoom factor must be a positive finite number: {factor}")
        factor = min(self.MAX_ZOOM, max(self.MIN_ZOOM, factor))
        current = self.zoom_factor()
        if abs(current - factor) < 1e-9:
            return
        self.scale(factor / current, factor / current)
        self.evt_zoom_changed.emit(self.zoom_factor())

    def zoom_in(self) -> None:
        """Increase the canvas scale by one zoom step."""
        self.set_zoom_factor(self.zoom_factor() * self.ZOOM_STEP)

    def zoom_out(self) -> None:
        """Decrease the canvas scale by one zoom step."""
        self.set_zoom_factor(self.zoom_factor() / self.ZOOM_STEP)

    def reset_zoom(self) -> None:
        """Restore the canvas to its unscaled view."""
        previous_zoom = self.zoom_factor()
        self.resetTransform()
        self._emit_zoom_changed(previous_zoom)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom around the mouse cursor in response to the wheel."""
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        factor = self.ZOOM_STEP ** (delta / 120.0)
        self.set_zoom_factor(self.zoom_factor() * factor)
        event.accept()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Paint the theme background and a zoom-aware dotted grid."""
        super().drawBackground(painter, rect)
        if not self._grid_visible:
            return
        spacing = self._effective_grid_spacing()
        left = floor(rect.left() / spacing) * spacing
        right = ceil(rect.right() / spacing) * spacing
        top = floor(rect.top() / spacing) * spacing
        bottom = ceil(rect.bottom() / spacing) * spacing
        color = THEMES.get_qt_color("primary")
        color.setAlpha(110)
        pen = QPen(color)
        pen.setWidthF(1.5)
        pen.setCosmetic(True)
        painter.save()
        painter.setPen(pen)
        y = top
        while y <= bottom:
            x = left
            while x <= right:
                painter.drawPoint(QPointF(x, y))
                x += spacing
            y += spacing
        painter.restore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle standard keyboard navigation shortcuts."""
        key = event.key()
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_in()
        elif key == Qt.Key.Key_Minus:
            self.zoom_out()
        elif key == Qt.Key.Key_0:
            self.reset_zoom()
        elif key == Qt.Key.Key_F:
            self.fit_to_view()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Select clicked nodes and clear selection on empty canvas clicks."""
        if event.button() == Qt.MouseButton.LeftButton:
            item: QGraphicsItem | None = self.itemAt(event.pos())
            while item is not None and not isinstance(item, _DependencyNodeItem):
                item = item.parentItem()
            if isinstance(item, _DependencyNodeItem):
                group_id = self._visible_to_group.get(item.node.id)
                if group_id is not None:
                    self._select_group(group_id)
                    self.evt_group_clicked.emit(group_id)
                else:
                    self.select_node(item.node.id)
                    self.evt_node_clicked.emit(item.node.id)
            else:
                self.select_node(None)
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double-click events to select nodes and emit the clicked signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            item: QGraphicsItem | None = self.itemAt(event.pos())
            while item is not None and not isinstance(item, _DependencyNodeItem):
                item = item.parentItem()
            if isinstance(item, _DependencyNodeItem):
                group_id = self._visible_to_group.get(item.node.id)
                if group_id is not None:
                    self.evt_group_double_clicked.emit(group_id)
                    self.set_group_collapsed(group_id, not self.is_group_collapsed(group_id))
                elif item.node.group in self._groups and not self.is_group_collapsed(item.node.group):
                    self.evt_group_double_clicked.emit(item.node.group)
                    self.set_group_collapsed(item.node.group, True)
                else:
                    self.evt_node_double_clicked.emit(item.node.id)
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()

    @staticmethod
    def _normalize_orientation(orientation: Orientation | Qt.Orientation) -> Orientation:
        if orientation in ("horizontal", Qt.Orientation.Horizontal):
            return "horizontal"
        if orientation in ("vertical", Qt.Orientation.Vertical):
            return "vertical"
        raise ValueError(f"Unsupported dependency graph orientation: {orientation}")

    def _emit_zoom_changed(self, previous_zoom: float) -> None:
        current_zoom = self.zoom_factor()
        if abs(current_zoom - previous_zoom) >= 1e-9:
            self.evt_zoom_changed.emit(current_zoom)

    def _validate_nodes(
        self,
        nodes: Sequence[DependencyGraphNode | Mapping[str, object]],
    ) -> tuple[list[DependencyGraphNode], dict[str, list[str]]]:
        validated = [
            self._copy_node(node) if isinstance(node, DependencyGraphNode) else DependencyGraphNode.parse_obj(node)
            for node in nodes
        ]
        for node in validated:
            node.icon = self._copy_icon(node.icon)
            self._resolve_icon(node.icon)
            node.group = self._normalize_group_id(node.group)
        node_ids = [node.id for node in validated]
        if any(not node_id.strip() for node_id in node_ids):
            raise ValueError("Dependency graph node IDs cannot be empty")
        if any(not node.title.strip() for node in validated):
            raise ValueError("Dependency graph node titles cannot be empty")
        if any(not node.state.strip() for node in validated):
            raise ValueError("Dependency graph node states cannot be empty")
        missing_states = {node.state for node in validated}.difference(self._state_colors)
        if missing_states:
            names = ", ".join(sorted(missing_states))
            raise ValueError(f"No colors configured for node states: {names}")
        if len(node_ids) != len(set(node_ids)):
            duplicates = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
            raise ValueError(f"Duplicate dependency graph node IDs: {', '.join(duplicates)}")

        known_ids = set(node_ids)
        dependants = {node_id: [] for node_id in node_ids}
        for node in validated:
            if len(node.dependencies) != len(set(node.dependencies)):
                raise ValueError(f"Node '{node.id}' contains duplicate dependencies")
            if node.id in node.dependencies:
                raise ValueError(f"Node '{node.id}' cannot depend on itself")
            unknown = sorted(set(node.dependencies).difference(known_ids))
            if unknown:
                raise ValueError(f"Node '{node.id}' has unknown dependencies: {', '.join(unknown)}")
            for dependency_id in node.dependencies:
                dependants[dependency_id].append(node.id)

        indegree = {node.id: len(node.dependencies) for node in validated}
        queue = deque(node_id for node_id in node_ids if indegree[node_id] == 0)
        visited = 0
        while queue:
            node_id = queue.popleft()
            visited += 1
            for dependant_id in dependants[node_id]:
                indegree[dependant_id] -= 1
                if indegree[dependant_id] == 0:
                    queue.append(dependant_id)
        if visited != len(validated):
            raise ValueError("Dependency graph contains a cycle")
        return validated, dependants

    def _rebuild_scene(self, positions: Mapping[str, tuple[float, float]] | None = None) -> None:
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._build_visible_graph()
        if self._selected_node_id is not None:
            self._selected_visible_id = self._node_to_visible_id.get(self._selected_node_id)
        elif self._selected_visible_id not in self._visible_dependencies:
            self._selected_visible_id = None
        self._edges_by_node = {node.id: [] for node in self._visible_nodes}
        if not self._nodes:
            self._scene.setSceneRect(QRectF())
            return
        self._rebuilding_scene = True
        try:
            for node in self._visible_nodes:
                group_id = self._visible_to_group.get(node.id)
                item = _DependencyNodeItem(
                    node,
                    self._orientation,
                    self._group_state_color(group_id) if group_id is not None else self._state_color(node.state),
                    has_input=bool(self._visible_dependencies[node.id]),
                    has_output=bool(self._visible_dependants[node.id]),
                    icon_resolver=self._resolve_icon,
                    position_changed=self._on_node_position_changed,
                    drag_finished=self._on_node_drag_finished,
                    movable=self._nodes_movable,
                )
                self._scene.addItem(item)
                self._node_items[node.id] = item

            self._layout_nodes()
            for node_id, position in (positions or {}).items():
                if node_id in self._node_items:
                    self._node_items[node_id].setPos(*position)
            for group_id, position in self._group_positions.items():
                if group_id not in self._manual_group_positions:
                    continue
                visible_id = self._group_visible_id(group_id)
                if visible_id in self._node_items:
                    self._node_items[visible_id].setPos(*position)
            for target in self._visible_nodes:
                for source_id in self._visible_dependencies[target.id]:
                    edge = _DependencyEdgeItem(
                        self._node_items[source_id],
                        self._node_items[target.id],
                        self._orientation,
                    )
                    self._scene.addItem(edge)
                    self._edge_items[(source_id, target.id)] = edge
                    self._edges_by_node[source_id].append(edge)
                    self._edges_by_node[target.id].append(edge)
        finally:
            self._rebuilding_scene = False
        self._update_scene_rect()
        self._update_highlights()
        self._remember_visible_positions()

    def _layout_nodes(self) -> None:
        levels = {node.id: 0 for node in self._visible_nodes}
        indegree = {node.id: len(self._visible_dependencies[node.id]) for node in self._visible_nodes}
        queue = deque(node.id for node in self._visible_nodes if indegree[node.id] == 0)
        while queue:
            node_id = queue.popleft()
            for dependant_id in self._visible_dependants[node_id]:
                levels[dependant_id] = max(levels[dependant_id], levels[node_id] + 1)
                indegree[dependant_id] -= 1
                if indegree[dependant_id] == 0:
                    queue.append(dependant_id)

        layer_ids: dict[int, list[str]] = {}
        for node in self._visible_nodes:
            layer_ids.setdefault(levels[node.id], []).append(node.id)

        layer_extents: dict[int, float] = {}
        for level, ids in layer_ids.items():
            sizes = [self._cross_size(self._node_items[node_id]) for node_id in ids]
            layer_extents[level] = sum(sizes) + self.NODE_SPACING * max(0, len(sizes) - 1)
        max_cross_extent = max(layer_extents.values())

        main_position = 0.0
        for level in sorted(layer_ids):
            ids = layer_ids[level]
            cross_position = (max_cross_extent - layer_extents[level]) / 2.0
            main_size = max(self._main_size(self._node_items[node_id]) for node_id in ids)
            for node_id in ids:
                item = self._node_items[node_id]
                if self._orientation == "horizontal":
                    item.setPos(main_position, cross_position)
                else:
                    item.setPos(cross_position, main_position)
                cross_position += self._cross_size(item) + self.NODE_SPACING
            main_position += main_size + self.LAYER_SPACING

    def _main_size(self, item: _DependencyNodeItem) -> float:
        return item.card_rect().width() if self._orientation == "horizontal" else item.card_rect().height()

    def _cross_size(self, item: _DependencyNodeItem) -> float:
        return item.card_rect().height() if self._orientation == "horizontal" else item.card_rect().width()

    def _refresh_groups(self) -> None:
        groups: dict[str, list[str]] = {}
        for node in self._nodes:
            if node.group is not None:
                groups.setdefault(node.group, []).append(node.id)
        self._groups = {group_id: tuple(node_ids) for group_id, node_ids in groups.items() if len(node_ids) > 1}
        self._group_collapsed = {group_id: self._group_collapsed.get(group_id, True) for group_id in self._groups}

    def _build_visible_graph(self) -> None:
        self._visible_nodes = []
        self._visible_dependencies = {}
        self._visible_dependants = {}
        self._visible_to_group = {}
        self._node_to_visible_id = {}

        added: set[str] = set()
        for node in self._nodes:
            visible_id = self._visible_id_for_node(node.id)
            self._node_to_visible_id[node.id] = visible_id
            if visible_id in added:
                continue
            added.add(visible_id)
            group_id = self._group_from_visible_id(visible_id)
            if group_id is None:
                self._visible_nodes.append(self._copy_node(node))
            else:
                self._visible_to_group[visible_id] = group_id
                self._visible_nodes.append(self._make_group_node(group_id))

        self._visible_dependencies = {node.id: () for node in self._visible_nodes}
        dependency_lists: dict[str, list[str]] = {node.id: [] for node in self._visible_nodes}
        dependant_lists: dict[str, list[str]] = {node.id: [] for node in self._visible_nodes}
        for target in self._nodes:
            target_visible_id = self._node_to_visible_id[target.id]
            for source_id in target.dependencies:
                source_visible_id = self._node_to_visible_id[source_id]
                if source_visible_id == target_visible_id:
                    continue
                if source_visible_id not in dependency_lists[target_visible_id]:
                    dependency_lists[target_visible_id].append(source_visible_id)
                    dependant_lists[source_visible_id].append(target_visible_id)
        self._visible_dependencies = {node_id: tuple(ids) for node_id, ids in dependency_lists.items()}
        self._visible_dependants = dependant_lists

    def _visible_id_for_node(self, node_id: str) -> str:
        group_id = self._nodes_by_id[node_id].group
        if group_id is not None and group_id in self._groups and self._group_collapsed.get(group_id, True):
            return self._group_visible_id(group_id)
        return node_id

    def _make_group_node(self, group_id: str) -> DependencyGraphNode:
        members = [self._nodes_by_id[node_id] for node_id in self._groups[group_id]]
        titles = {member.title for member in members}
        states: dict[str, int] = {}
        for member in members:
            states[member.state] = states.get(member.state, 0) + 1
        state_parts = [f"{state.replace('-', ' ').replace('_', ' ')}: {count}" for state, count in states.items()]
        shared_state = next(iter(states)) if len(states) == 1 else "group"
        title = members[0].title if len(titles) == 1 else group_id
        description = f"{len(members)} tasks"
        if state_parts:
            description = f"{description}\n{', '.join(state_parts)}"
        return DependencyGraphNode(
            id=self._group_visible_id(group_id),
            title=title,
            description=description,
            state=shared_state,
        )

    def _group_state_color(self, group_id: str | None) -> QColor:
        if group_id is None:
            return THEMES.get_qt_color("secondary")
        states = {self._nodes_by_id[node_id].state for node_id in self._groups[group_id]}
        if len(states) == 1:
            return self._state_color(next(iter(states)))
        return THEMES.get_qt_color("secondary")

    def _state_color(self, state: str) -> QColor:
        return QColor(self._state_colors[state])

    @staticmethod
    def _copy_icon(icon: QIcon | str | None) -> QIcon | str | None:
        return QIcon(icon) if isinstance(icon, QIcon) else icon

    @classmethod
    def _copy_node(cls, node: DependencyGraphNode) -> DependencyGraphNode:
        return DependencyGraphNode(
            id=node.id,
            title=node.title,
            description=node.description,
            dependencies=tuple(node.dependencies),
            state=node.state,
            icon=cls._copy_icon(node.icon),
            group=node.group,
        )

    @staticmethod
    def _resolve_icon(icon: QIcon | str | None) -> QIcon | None:
        if icon is None:
            return None
        if isinstance(icon, QIcon):
            return QIcon(icon)
        icon_name = icon.strip()
        if not icon_name:
            raise ValueError("Dependency graph node icon aliases cannot be empty")
        from qtextra.helpers import make_qta_icon

        return make_qta_icon(icon_name)

    @staticmethod
    def _validate_grid_spacing(spacing: float) -> float:
        spacing = float(spacing)
        if not isfinite(spacing) or spacing <= 0.0:
            raise ValueError(f"Grid spacing must be a positive finite number: {spacing}")
        return spacing

    @staticmethod
    def _normalize_position(position: QPointF | tuple[float, float]) -> QPointF:
        if isinstance(position, QPointF):
            point = QPointF(position)
        else:
            try:
                x, y = position
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Node positions must contain exactly two coordinates: {position}") from exc
            point = QPointF(float(x), float(y))
        if not isfinite(point.x()) or not isfinite(point.y()):
            raise ValueError(f"Node positions must contain finite coordinates: {position}")
        return point

    def _effective_grid_spacing(self) -> float:
        spacing = self._grid_spacing
        zoom = max(self.zoom_factor(), 1e-9)
        while spacing * zoom < self.MIN_GRID_SCREEN_SPACING:
            spacing *= 2.0
        return spacing

    def _snap_position(self, position: QPointF) -> QPointF:
        spacing = self._grid_spacing
        return QPointF(round(position.x() / spacing) * spacing, round(position.y() / spacing) * spacing)

    def _remember_visible_positions(self) -> None:
        for visible_id, item in self._node_items.items():
            position = (item.pos().x(), item.pos().y())
            group_id = self._visible_to_group.get(visible_id)
            if group_id is None:
                self._node_positions[visible_id] = position
            else:
                self._group_positions[group_id] = position

    def _manual_visible_positions(self) -> dict[str, tuple[float, float]]:
        return {
            node_id: self._node_positions[node_id]
            for node_id in self._manual_node_positions
            if node_id in self._node_positions
        }

    def _on_node_position_changed(self, node_id: str) -> None:
        if self._rebuilding_scene:
            return
        for edge in self._edges_by_node.get(node_id, []):
            edge.update_path()

    def _on_node_drag_finished(self, node_id: str, start_position: QPointF) -> None:
        item = self._node_items[node_id]
        if item.pos() == start_position:
            return
        if self._snap_to_grid:
            item.setPos(self._snap_position(item.pos()))
        self._update_scene_rect()
        group_id = self._visible_to_group.get(node_id)
        if group_id is not None:
            self._group_positions[group_id] = (item.pos().x(), item.pos().y())
            self._manual_group_positions.add(group_id)
        elif item.pos() != start_position:
            self._node_positions[node_id] = (item.pos().x(), item.pos().y())
            self._manual_node_positions.add(node_id)
            self.evt_node_moved.emit(node_id, QPointF(item.pos()))

    def _update_all_edges(self) -> None:
        for edge in self._edge_items.values():
            edge.update_path()

    def _update_scene_rect(self) -> None:
        if self._updating_scene_rect:
            return
        self._updating_scene_rect = True
        try:
            bounds = self._scene.itemsBoundingRect().adjusted(
                -self.SCENE_MARGIN,
                -self.SCENE_MARGIN,
                self.SCENE_MARGIN,
                self.SCENE_MARGIN,
            )
            self._scene.setSceneRect(bounds)
        finally:
            self._updating_scene_rect = False

    @staticmethod
    def _normalize_state(state: str | TaskState) -> str:
        state_name = state.value if isinstance(state, TaskState) else str(state)
        state_name = state_name.strip()
        if not state_name:
            raise ValueError("Dependency graph node states cannot be empty")
        return state_name

    @classmethod
    def _group_visible_id(cls, group_id: str) -> str:
        return f"{cls.GROUP_ID_PREFIX}{group_id}"

    @classmethod
    def _group_from_visible_id(cls, visible_id: str) -> str | None:
        if visible_id.startswith(cls.GROUP_ID_PREFIX):
            return visible_id.removeprefix(cls.GROUP_ID_PREFIX)
        return None

    @staticmethod
    def _normalize_group_id(group_id: object, *, allow_empty: bool = True) -> str | None:
        if group_id is None:
            if allow_empty:
                return None
            raise ValueError("Dependency graph group IDs cannot be empty")
        normalized = str(group_id).strip()
        if normalized:
            return normalized
        if allow_empty:
            return None
        raise ValueError("Dependency graph group IDs cannot be empty")

    def _select_group(self, group_id: str) -> None:
        previous_node = self._selected_node_id
        self._selected_node_id = None
        self._selected_visible_id = self._group_visible_id(group_id)
        self._update_highlights()
        if previous_node is not None:
            self.evt_selection_changed.emit(None)

    def _walk(self, node_id: str, adjacency: Mapping[str, Sequence[str]]) -> set[str]:
        related: set[str] = set()
        queue = deque(adjacency[node_id])
        while queue:
            related_id = queue.popleft()
            if related_id in related:
                continue
            related.add(related_id)
            queue.extend(adjacency[related_id])
        return related

    def _update_highlights(self) -> None:
        selected = self._selected_visible_id
        if selected is None:
            for item in self._node_items.values():
                item.set_relation("normal")
            for edge in self._edge_items.values():
                edge.set_relation("normal")
            return

        upstream = self._walk(selected, self._visible_dependencies)
        downstream = self._walk(selected, self._visible_dependants)
        for node_id, item in self._node_items.items():
            if node_id == selected:
                relation = "selected"
            elif node_id in upstream:
                relation = "upstream"
            elif node_id in downstream:
                relation = "downstream"
            else:
                relation = "unrelated"
            item.set_relation(relation)

        for (source_id, target_id), edge in self._edge_items.items():
            if source_id in upstream and target_id in upstream | {selected}:
                relation = "upstream"
            elif source_id in downstream | {selected} and target_id in downstream:
                relation = "downstream"
            else:
                relation = "unrelated"
            edge.set_relation(relation)

    def _apply_theme(self) -> None:
        self.setBackgroundBrush(QBrush(THEMES.get_qt_color("background")))
        for node_id, item in self._node_items.items():
            group_id = self._visible_to_group.get(node_id)
            if group_id is not None:
                item.set_state(item.node.state, self._group_state_color(group_id))
            item.refresh_theme()
        self._update_highlights()
        self.viewport().update()
