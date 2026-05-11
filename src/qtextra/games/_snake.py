"""Minimal Snake game dialog."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from enum import Enum

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent, QPen
from qtpy.QtWidgets import QWidget

from qtextra.config.theme import THEMES
from qtextra.games._base import GameBoardWidget, GameDialogMixin
from qtextra.widgets.qt_dialog import QtDialog

BOARD_SIZE = 16
TICK_INTERVAL_MS = 150


class SnakeDirection(Enum):
    """Cardinal movement direction for the snake."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self) -> tuple[int, int]:
        """Return the per-step position delta."""
        return self.value


@dataclass(frozen=True, slots=True)
class GridPoint:
    """A single board coordinate."""

    x: int
    y: int

    def moved(self, direction: SnakeDirection) -> GridPoint:
        """Return a new point moved by one cell."""
        dx, dy = direction.delta
        return GridPoint(self.x + dx, self.y + dy)


@dataclass(frozen=True, slots=True)
class SnakeGameState:
    """Immutable Snake game state."""

    width: int
    height: int
    snake: tuple[GridPoint, ...]
    food: GridPoint | None
    score: int
    direction: SnakeDirection
    last_direction: SnakeDirection
    has_started: bool
    is_game_over: bool


def is_opposite_direction(current: SnakeDirection, candidate: SnakeDirection) -> bool:
    """Return whether two directions are opposites."""
    dx_current, dy_current = current.delta
    dx_candidate, dy_candidate = candidate.delta
    return dx_current == -dx_candidate and dy_current == -dy_candidate


def spawn_food(width: int, height: int, snake: tuple[GridPoint, ...], rng: random.Random) -> GridPoint | None:
    """Spawn food on a free cell, or return ``None`` if the board is full."""
    occupied = set(snake)
    free_cells = [GridPoint(x, y) for y in range(height) for x in range(width) if GridPoint(x, y) not in occupied]
    if not free_cells:
        return None
    return rng.choice(free_cells)


def create_initial_state(
    width: int = BOARD_SIZE, height: int = BOARD_SIZE, rng: random.Random | None = None
) -> SnakeGameState:
    """Create a fresh game state."""
    if width < 4 or height < 4:
        msg = "Snake board must be at least 4x4."
        raise ValueError(msg)

    generator = rng if rng is not None else random.Random()
    center_x = width // 2
    center_y = height // 2
    snake = (
        GridPoint(center_x, center_y),
        GridPoint(center_x - 1, center_y),
        GridPoint(center_x - 2, center_y),
    )
    food = spawn_food(width, height, snake, generator)
    return SnakeGameState(
        width=width,
        height=height,
        snake=snake,
        food=food,
        score=0,
        direction=SnakeDirection.RIGHT,
        last_direction=SnakeDirection.RIGHT,
        has_started=False,
        is_game_over=False,
    )


def change_direction(state: SnakeGameState, direction: SnakeDirection) -> SnakeGameState:
    """Return a state with an updated direction when the move is valid."""
    if state.is_game_over:
        return state
    reference = state.last_direction if state.has_started else state.direction
    if is_opposite_direction(reference, direction):
        return state
    return replace(state, direction=direction)


def advance_state(state: SnakeGameState, rng: random.Random) -> SnakeGameState:
    """Advance the snake by one tick."""
    if state.is_game_over:
        return state

    head = state.snake[0]
    next_head = head.moved(state.direction)
    grows = state.food is not None and next_head == state.food
    collision_body = state.snake if grows else state.snake[:-1]

    if not (0 <= next_head.x < state.width and 0 <= next_head.y < state.height):
        return replace(state, has_started=True, is_game_over=True, last_direction=state.direction)
    if next_head in collision_body:
        return replace(state, has_started=True, is_game_over=True, last_direction=state.direction)

    if grows:
        new_snake = (next_head, *state.snake)
        food = spawn_food(state.width, state.height, new_snake, rng)
        score = state.score + 1
        is_game_over = food is None
    else:
        new_snake = (next_head, *state.snake[:-1])
        food = state.food
        score = state.score
        is_game_over = False

    return SnakeGameState(
        width=state.width,
        height=state.height,
        snake=new_snake,
        food=food,
        score=score,
        direction=state.direction,
        last_direction=state.direction,
        has_started=True,
        is_game_over=is_game_over,
    )


class SnakeBoardWidget(GameBoardWidget):
    """Paint the Snake game board."""

    _state: SnakeGameState | None  # narrowed from GameBoardWidget

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the board widget."""
        super().__init__(parent)
        self.setMinimumSize(320, 320)

    def sizeHint(self) -> QSize:
        """Return the preferred board size."""
        return QSize(360, 360)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the current board state."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        background = self.palette().color(self.backgroundRole())
        board_background = background.darker(112) if THEMES.is_dark else background.lighter(104)
        grid_color = background.lighter(140) if THEMES.is_dark else background.darker(112)
        snake_color = QColor(THEMES.get_hex_color("success"))
        food_color = QColor(THEMES.get_hex_color("warning"))

        painter.fillRect(self.rect(), board_background)

        if self._state is None:
            return

        cell_size = min(self.width() / self._state.width, self.height() / self._state.height)
        board_width = cell_size * self._state.width
        board_height = cell_size * self._state.height
        origin_x = (self.width() - board_width) / 2
        origin_y = (self.height() - board_height) / 2

        painter.setPen(QPen(grid_color, 1))
        for x in range(self._state.width + 1):
            px = round(origin_x + x * cell_size)
            painter.drawLine(px, round(origin_y), px, round(origin_y + board_height))
        for y in range(self._state.height + 1):
            py = round(origin_y + y * cell_size)
            painter.drawLine(round(origin_x), py, round(origin_x + board_width), py)

        for index, point in enumerate(reversed(self._state.snake)):
            rect_x = round(origin_x + point.x * cell_size + 1)
            rect_y = round(origin_y + point.y * cell_size + 1)
            rect_size = max(1, round(cell_size - 2))
            color = snake_color.lighter(120) if index == len(self._state.snake) - 1 else snake_color
            painter.fillRect(rect_x, rect_y, rect_size, rect_size, color)

        if self._state.food is not None:
            rect_x = round(origin_x + self._state.food.x * cell_size + 2)
            rect_y = round(origin_y + self._state.food.y * cell_size + 2)
            rect_size = max(1, round(cell_size - 4))
            painter.fillRect(rect_x, rect_y, rect_size, rect_size, food_color)

        if self._state.is_game_over:
            painter.fillRect(self.rect(), self._game_over_overlay(80))


class SnakeDialog(GameDialogMixin, QtDialog):
    """Standalone dialog that hosts a minimal Snake game."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        width: int = BOARD_SIZE,
        height: int = BOARD_SIZE,
        tick_interval_ms: int = TICK_INTERVAL_MS,
        rng: random.Random | None = None,
    ) -> None:
        """Initialize the Snake dialog."""
        self._board_width = width
        self._board_height = height
        self._tick_interval_ms = tick_interval_ms
        self._rng = rng if rng is not None else random.Random()
        self._state = create_initial_state(width=width, height=height, rng=self._rng)
        self._is_paused = False
        super().__init__(parent, title="Snake Game")
        self.setMinimumSize(420, 520)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_game_timer(self._tick_interval_ms)
        self.restart_game()

    # ── GameDialogMixin interface ──────────────────────────────────────────────

    def _create_board_widget(self) -> SnakeBoardWidget:
        """Return the snake board widget."""
        return SnakeBoardWidget(self)

    def _instructions_text(self) -> str:
        """Return keyboard instructions."""
        return "Arrow keys or WASD to move. Space pauses. R restarts."

    def _do_restart(self) -> None:
        """Reset game state for a new round."""
        self._state = create_initial_state(width=self._board_width, height=self._board_height, rng=self._rng)

    def _do_advance_state(self) -> None:
        """Advance the snake by one tick."""
        self._state = advance_state(self._state, self._rng)

    # ── keyboard handling ──────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Handle keyboard controls for the game."""
        if event is None:
            return

        key = event.key()
        direction_map = {
            Qt.Key.Key_Up: SnakeDirection.UP,
            Qt.Key.Key_W: SnakeDirection.UP,
            Qt.Key.Key_Down: SnakeDirection.DOWN,
            Qt.Key.Key_S: SnakeDirection.DOWN,
            Qt.Key.Key_Left: SnakeDirection.LEFT,
            Qt.Key.Key_A: SnakeDirection.LEFT,
            Qt.Key.Key_Right: SnakeDirection.RIGHT,
            Qt.Key.Key_D: SnakeDirection.RIGHT,
        }

        if key in direction_map:
            self._state = change_direction(self._state, direction_map[key])
            self._refresh_ui()
            event.accept()
            return
        if key == Qt.Key.Key_Space:
            self.toggle_pause()
            event.accept()
            return
        if key == Qt.Key.Key_R:
            self.restart_game()
            event.accept()
            return

        super().keyPressEvent(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    _ = qapplication()  # analysis:ignore
    dlg = SnakeDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
