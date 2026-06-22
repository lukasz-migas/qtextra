"""Scrollable dependency graph widget for stateful tasks."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from math import isfinite
from typing import ClassVar

from qtpy.QtCore import Property, QPointF, QRectF, Qt, Signal
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
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


class _DependencyNodeItem(QGraphicsObject):
    """Paint one task card and its derived connection ports."""

    WIDTH: ClassVar[float] = 240.0
    MIN_HEIGHT: ClassVar[float] = 112.0
    PADDING: ClassVar[float] = 14.0
    ACCENT_WIDTH: ClassVar[float] = 6.0
    PORT_RADIUS: ClassVar[float] = 5.0
    TITLE_GAP: ClassVar[float] = 8.0
    DESCRIPTION_GAP: ClassVar[float] = 10.0

    def __init__(
        self,
        node: DependencyGraphNode,
        orientation: Orientation,
        state_color: QColor,
        has_input: bool,
        has_output: bool,
    ) -> None:
        """Initialize a task card."""
        super().__init__()
        self.node = node
        self.orientation = orientation
        self.state_color = QColor(state_color)
        self.has_input = has_input
        self.has_output = has_output
        self.relation = "normal"
        self._title_font = QFont()
        self._title_font.setBold(True)
        self._state_font = QFont()
        self._state_font.setPointSizeF(max(7.0, self._state_font.pointSizeF() - 1.0))
        self._description_font = QFont()
        self._height = self.MIN_HEIGHT
        self._update_height()
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

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
        self.update()

    def set_state(self, state: str, color: QColor) -> None:
        """Update state data and repaint without changing graph geometry."""
        self.node.state = state
        self.state_color = QColor(color)
        self.update()

    def refresh_theme(self) -> None:
        """Repaint the node using the active application theme."""
        self.update()

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

        title_width = max(20.0, content_width - state_width - self.TITLE_GAP)
        title_rect = QRectF(content_left, self.PADDING, title_width, state_height)
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
    evt_selection_changed = Signal(object)
    evt_node_state_changed = Signal(str, object)
    evt_zoom_changed = Signal(float)

    LAYER_SPACING: ClassVar[float] = 110.0
    NODE_SPACING: ClassVar[float] = 42.0
    SCENE_MARGIN: ClassVar[float] = 40.0
    ZOOM_STEP: ClassVar[float] = 1.2
    MIN_ZOOM: ClassVar[float] = 0.1
    MAX_ZOOM: ClassVar[float] = 4.0

    def __init__(
        self,
        nodes: Sequence[DependencyGraphNode | Mapping[str, object]] | None = None,
        orientation: Orientation | Qt.Orientation = "horizontal",
        state_colors: Mapping[str | TaskState, QColor | str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the graph view with optional node data."""
        self._scene = QGraphicsScene()
        super().__init__(self._scene, parent)
        self._orientation = self._normalize_orientation(orientation)
        self._nodes: list[DependencyGraphNode] = []
        self._nodes_by_id: dict[str, DependencyGraphNode] = {}
        self._dependencies: dict[str, tuple[str, ...]] = {}
        self._dependants: dict[str, list[str]] = {}
        self._node_items: dict[str, _DependencyNodeItem] = {}
        self._edge_items: dict[tuple[str, str], _DependencyEdgeItem] = {}
        self._selected_node_id: str | None = None
        self._state_colors: dict[str, QColor] = {}

        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.set_state_colors(state_colors)
        THEMES.evt_theme_changed.connect(self._apply_theme)
        self._apply_theme()
        if nodes is not None:
            self.set_nodes(nodes)

    def get_nodes(self) -> list[DependencyGraphNode]:
        """Return deep copies of the configured graph nodes."""
        return [node.copy(deep=True) for node in self._nodes]

    def set_nodes(self, nodes: Sequence[DependencyGraphNode | Mapping[str, object]]) -> None:
        """Validate and replace all task nodes, leaving the old graph intact on failure."""
        validated, dependants = self._validate_nodes(nodes)
        previous_selection = self._selected_node_id
        self._nodes = validated
        self._nodes_by_id = {node.id: node for node in validated}
        self._dependencies = {node.id: node.dependencies for node in validated}
        self._dependants = dependants
        self._selected_node_id = None
        self._rebuild_scene()
        if previous_selection is not None:
            self.evt_selection_changed.emit(None)

    def clear(self) -> None:
        """Remove every node, edge, and active selection from the graph."""
        self.set_nodes([])

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
            item.set_state(item.node.state, self._state_color(self._nodes_by_id[node_id].state))

    def set_node_state(self, node_id: str, state: str | TaskState) -> None:
        """Update one node state without rebuilding or repositioning the graph."""
        if node_id not in self._nodes_by_id:
            raise KeyError(f"Unknown dependency graph node: {node_id}")
        state_name = self._normalize_state(state)
        if state_name not in self._state_colors:
            raise ValueError(f"No color configured for node state: {state_name}")
        self._nodes_by_id[node_id].state = state_name
        self._node_items[node_id].set_state(state_name, self._state_color(state_name))
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
        self._update_highlights()
        if changed:
            self.evt_selection_changed.emit(node_id)

    def center_on_node(self, node_id: str) -> None:
        """Center the viewport on a graph node."""
        if node_id not in self._node_items:
            raise KeyError(f"Unknown dependency graph node: {node_id}")
        self.centerOn(self._node_items[node_id])

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

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Select clicked nodes and clear selection on empty canvas clicks."""
        if event.button() == Qt.MouseButton.LeftButton:
            item: QGraphicsItem | None = self.itemAt(event.pos())
            while item is not None and not isinstance(item, _DependencyNodeItem):
                item = item.parentItem()
            if isinstance(item, _DependencyNodeItem):
                self.select_node(item.node.id)
                self.evt_node_clicked.emit(item.node.id)
            else:
                self.select_node(None)
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click events to select nodes and emit the clicked signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            item: QGraphicsItem | None = self.itemAt(event.pos())
            while item is not None and not isinstance(item, _DependencyNodeItem):
                item = item.parentItem()
            if isinstance(item, _DependencyNodeItem):
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
            node.copy(deep=True) if isinstance(node, DependencyGraphNode) else DependencyGraphNode.parse_obj(node)
            for node in nodes
        ]
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

    def _rebuild_scene(self) -> None:
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        if not self._nodes:
            self._scene.setSceneRect(QRectF())
            return

        for node in self._nodes:
            item = _DependencyNodeItem(
                node,
                self._orientation,
                self._state_color(node.state),
                has_input=bool(node.dependencies),
                has_output=bool(self._dependants[node.id]),
            )
            self._scene.addItem(item)
            self._node_items[node.id] = item

        self._layout_nodes()
        for target in self._nodes:
            for source_id in target.dependencies:
                edge = _DependencyEdgeItem(
                    self._node_items[source_id],
                    self._node_items[target.id],
                    self._orientation,
                )
                self._scene.addItem(edge)
                self._edge_items[(source_id, target.id)] = edge
        bounds = self._scene.itemsBoundingRect().adjusted(
            -self.SCENE_MARGIN,
            -self.SCENE_MARGIN,
            self.SCENE_MARGIN,
            self.SCENE_MARGIN,
        )
        self._scene.setSceneRect(bounds)
        self._update_highlights()

    def _layout_nodes(self) -> None:
        levels = {node.id: 0 for node in self._nodes}
        indegree = {node.id: len(node.dependencies) for node in self._nodes}
        queue = deque(node.id for node in self._nodes if indegree[node.id] == 0)
        while queue:
            node_id = queue.popleft()
            for dependant_id in self._dependants[node_id]:
                levels[dependant_id] = max(levels[dependant_id], levels[node_id] + 1)
                indegree[dependant_id] -= 1
                if indegree[dependant_id] == 0:
                    queue.append(dependant_id)

        layer_ids: dict[int, list[str]] = {}
        for node in self._nodes:
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

    def _state_color(self, state: str) -> QColor:
        return QColor(self._state_colors[state])

    @staticmethod
    def _normalize_state(state: str | TaskState) -> str:
        state_name = state.value if isinstance(state, TaskState) else str(state)
        state_name = state_name.strip()
        if not state_name:
            raise ValueError("Dependency graph node states cannot be empty")
        return state_name

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
        selected = self._selected_node_id
        if selected is None:
            for item in self._node_items.values():
                item.set_relation("normal")
            for edge in self._edge_items.values():
                edge.set_relation("normal")
            return

        upstream = self._walk(selected, self._dependencies)
        downstream = self._walk(selected, self._dependants)
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
        for item in self._node_items.values():
            item.refresh_theme()
        self._update_highlights()
        self.viewport().update()
