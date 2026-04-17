"""Minimal Snake game dialog."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from enum import Enum

from qtpy.QtCore import QSize, Qt, QTimer
from qtpy.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent, QPen
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config.theme import THEMES
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


class SnakeBoardWidget(QWidget):
    """Paint the Snake game board."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the board widget."""
        super().__init__(parent)
        self._state: SnakeGameState | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 320)

    def sizeHint(self) -> QSize:
        """Return the preferred board size."""
        return QSize(360, 360)

    def set_state(self, state: SnakeGameState) -> None:
        """Store state and schedule a repaint."""
        self._state = state
        self.update()

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
        game_over_overlay = QColor(THEMES.get_hex_color("error"))
        game_over_overlay.setAlpha(80)

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
            painter.fillRect(self.rect(), game_over_overlay)


class SnakeDialog(QtDialog):
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

        self.timer = QTimer(self)
        self.timer.setInterval(self._tick_interval_ms)
        self.timer.timeout.connect(self.advance_game)

        self.restart_game()

    def make_panel(self) -> QVBoxLayout:
        """Build the dialog layout."""
        self.score_label = hp.make_label(self, "", bold=True, alignment=Qt.AlignmentFlag.AlignLeft)
        self.status_label = hp.make_label(self, "", alignment=Qt.AlignmentFlag.AlignRight)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.score_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.status_label)

        self.board_widget = SnakeBoardWidget(self)

        self.instructions_label = hp.make_label(
            self,
            "Arrow keys or WASD to move. Space pauses. R restarts.",
            wrap=True,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        self.pause_button = hp.make_btn(self, "Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.restart_button = hp.make_btn(self, "Restart")
        self.restart_button.clicked.connect(self.restart_game)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.restart_button)

        layout = hp.make_v_layout()
        layout.addLayout(header_layout)
        layout.addWidget(self.board_widget, stretch=1)
        layout.addWidget(self.instructions_label)
        layout.addLayout(button_layout)
        return layout

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop the timer when the dialog closes."""
        self.timer.stop()
        super().closeEvent(event)

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

    def restart_game(self) -> None:
        """Reset the game state and start a new round."""
        self._state = create_initial_state(width=self._board_width, height=self._board_height, rng=self._rng)
        self._is_paused = False
        self.timer.start()
        self._refresh_ui()
        self.setFocus()

    def toggle_pause(self) -> None:
        """Pause or resume the running game."""
        if self._state.is_game_over:
            self.setFocus()
            return
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.timer.stop()
        else:
            self.timer.start()
        self._refresh_ui()
        self.setFocus()

    def advance_game(self) -> None:
        """Advance the game by one timer tick."""
        if self._is_paused or self._state.is_game_over:
            return
        self._state = advance_state(self._state, self._rng)
        if self._state.is_game_over:
            self.timer.stop()
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Synchronize labels and board painting from the current state."""
        self.score_label.setText(f"Score: {self._state.score}")
        if self._state.is_game_over:
            status = "Game over"
            pause_text = "Pause"
        elif self._is_paused:
            status = "Paused"
            pause_text = "Resume"
        else:
            status = "Running"
            pause_text = "Pause"
        self.status_label.setText(status)
        self.pause_button.setText(pause_text)
        self.board_widget.set_state(self._state)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from ionglow.utils.dev import apply_style, qapplication

    _ = qapplication()  # analysis:ignore
    dlg = SnakeDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
