"""Minimal Chrome-style dinosaur game dialog."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent, QPen
from qtpy.QtWidgets import QWidget

from qtextra.config.theme import THEMES
from qtextra.games._base import GameBoardWidget, GameDialogMixin
from qtextra.widgets.qt_dialog import QtDialog

BOARD_WIDTH = 720
BOARD_HEIGHT = 240
GROUND_MARGIN = 36
DINO_X = 80
DINO_WIDTH = 36
DINO_HEIGHT = 42
GRAVITY = 1.1
JUMP_VELOCITY = -14.0
BASE_SPEED = 8.0
TICK_INTERVAL_MS = 32


@dataclass(frozen=True, slots=True)
class Obstacle:
    """A single ground obstacle."""

    x: float
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class DinosaurGameState:
    """Immutable dinosaur runner game state."""

    width: int
    height: int
    ground_y: int
    dino_x: int
    dino_width: int
    dino_height: int
    dino_y: float
    vertical_velocity: float
    obstacles: tuple[Obstacle, ...]
    score: int
    speed: float
    spawn_cooldown: int
    is_game_over: bool
    has_started: bool


def _make_obstacle(rng: random.Random, board_width: int) -> Obstacle:
    """Create a deterministic obstacle."""
    width, height = rng.choice(((18, 30), (22, 42), (28, 52)))
    offset = rng.randint(0, 40)
    return Obstacle(x=float(board_width + offset), width=width, height=height)


def _make_spawn_cooldown(rng: random.Random) -> int:
    """Create a deterministic obstacle spawn cooldown."""
    return rng.randint(18, 30)


def create_initial_state(
    *,
    width: int = BOARD_WIDTH,
    height: int = BOARD_HEIGHT,
    rng: random.Random | None = None,
) -> DinosaurGameState:
    """Create a fresh dinosaur runner state."""
    generator = rng if rng is not None else random.Random()
    ground_y = height - GROUND_MARGIN
    return DinosaurGameState(
        width=width,
        height=height,
        ground_y=ground_y,
        dino_x=DINO_X,
        dino_width=DINO_WIDTH,
        dino_height=DINO_HEIGHT,
        dino_y=float(ground_y - DINO_HEIGHT),
        vertical_velocity=0.0,
        obstacles=(),
        score=0,
        speed=BASE_SPEED,
        spawn_cooldown=_make_spawn_cooldown(generator),
        is_game_over=False,
        has_started=False,
    )


def jump_dinosaur(state: DinosaurGameState) -> DinosaurGameState:
    """Trigger a jump when the dinosaur is on the ground."""
    if state.is_game_over:
        return state
    ground_top = float(state.ground_y - state.dino_height)
    if state.dino_y < ground_top - 0.001:
        return state
    return replace(state, vertical_velocity=JUMP_VELOCITY, has_started=True)


def _rectangles_overlap(
    x1: float,
    y1: float,
    width1: int,
    height1: int,
    x2: float,
    y2: float,
    width2: int,
    height2: int,
) -> bool:
    """Return whether two axis-aligned rectangles overlap."""
    return x1 < x2 + width2 and x1 + width1 > x2 and y1 < y2 + height2 and y1 + height1 > y2


def advance_state(state: DinosaurGameState, rng: random.Random) -> DinosaurGameState:
    """Advance the dinosaur runner by one tick."""
    if state.is_game_over:
        return state

    ground_top = float(state.ground_y - state.dino_height)
    vertical_velocity = state.vertical_velocity + GRAVITY
    dino_y = state.dino_y + vertical_velocity
    if dino_y >= ground_top:
        dino_y = ground_top
        vertical_velocity = 0.0

    moved_obstacles = tuple(
        Obstacle(x=obstacle.x - state.speed, width=obstacle.width, height=obstacle.height)
        for obstacle in state.obstacles
        if obstacle.x + obstacle.width - state.speed > 0
    )

    spawn_cooldown = state.spawn_cooldown - 1
    if spawn_cooldown <= 0:
        moved_obstacles = (*moved_obstacles, _make_obstacle(rng, state.width))
        spawn_cooldown = _make_spawn_cooldown(rng)

    score = state.score + 1
    speed = min(state.speed + 0.015, 16.0)

    for obstacle in moved_obstacles:
        obstacle_y = state.ground_y - obstacle.height
        if _rectangles_overlap(
            float(state.dino_x),
            dino_y,
            state.dino_width,
            state.dino_height,
            obstacle.x,
            float(obstacle_y),
            obstacle.width,
            obstacle.height,
        ):
            return replace(
                state,
                dino_y=dino_y,
                vertical_velocity=vertical_velocity,
                obstacles=tuple(moved_obstacles),
                score=score,
                speed=speed,
                spawn_cooldown=spawn_cooldown,
                is_game_over=True,
                has_started=True,
            )

    return replace(
        state,
        dino_y=dino_y,
        vertical_velocity=vertical_velocity,
        obstacles=tuple(moved_obstacles),
        score=score,
        speed=speed,
        spawn_cooldown=spawn_cooldown,
        has_started=True,
    )


class DinosaurBoardWidget(GameBoardWidget):
    """Paint the dinosaur runner board."""

    _state: DinosaurGameState | None  # narrowed from GameBoardWidget

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the board widget."""
        super().__init__(parent)
        self.setMinimumSize(480, 220)

    def sizeHint(self) -> QSize:
        """Return the preferred board size."""
        return QSize(560, 240)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the current game state."""
        super().paintEvent(event)
        if self._state is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        background = self.palette().color(self.backgroundRole())
        sky_color = background
        ground_color = background.darker(116) if THEMES.is_dark else background.darker(108)
        line_color = QColor(THEMES.get_hex_color("primary"))
        dino_color = QColor(THEMES.get_hex_color("success"))
        obstacle_color = QColor(THEMES.get_hex_color("warning"))

        painter.fillRect(self.rect(), sky_color)

        scale_x = self.width() / self._state.width
        scale_y = self.height() / self._state.height
        ground_y = round(self._state.ground_y * scale_y)
        painter.fillRect(0, ground_y, self.width(), self.height() - ground_y, ground_color)
        painter.setPen(QPen(line_color, 2))
        painter.drawLine(0, ground_y, self.width(), ground_y)

        dino_x = round(self._state.dino_x * scale_x)
        dino_y = round(self._state.dino_y * scale_y)
        dino_width = round(self._state.dino_width * scale_x)
        dino_height = round(self._state.dino_height * scale_y)
        painter.fillRect(dino_x, dino_y, dino_width, dino_height, dino_color)

        for obstacle in self._state.obstacles:
            obstacle_x = round(obstacle.x * scale_x)
            obstacle_y = round((self._state.ground_y - obstacle.height) * scale_y)
            obstacle_width = round(obstacle.width * scale_x)
            obstacle_height = round(obstacle.height * scale_y)
            painter.fillRect(obstacle_x, obstacle_y, obstacle_width, obstacle_height, obstacle_color)

        if self._state.is_game_over:
            painter.fillRect(self.rect(), self._game_over_overlay(70))


class DinosaurDialog(GameDialogMixin, QtDialog):
    """Standalone dialog that hosts a minimal dinosaur runner."""

    def __init__(self, parent: QWidget | None, *, rng: random.Random | None = None) -> None:
        """Initialize the dinosaur dialog."""
        self._rng = rng if rng is not None else random.Random()
        self._state = create_initial_state(rng=self._rng)
        self._is_paused = False
        super().__init__(parent, title="Dinosaur Game")
        self.setMinimumSize(560, 400)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_game_timer(TICK_INTERVAL_MS)
        self.restart_game()

    # ── GameDialogMixin interface ──────────────────────────────────────────────

    def _create_board_widget(self) -> DinosaurBoardWidget:
        """Return the dinosaur board widget."""
        return DinosaurBoardWidget(self)

    def _instructions_text(self) -> str:
        """Return keyboard instructions."""
        return "Space, Up, or W jumps. P pauses. R restarts."

    def _do_restart(self) -> None:
        """Reset game state for a new run."""
        self._state = create_initial_state(rng=self._rng)

    def _do_advance_state(self) -> None:
        """Advance the runner by one tick."""
        self._state = advance_state(self._state, self._rng)

    # ── keyboard handling ──────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Handle keyboard controls."""
        if event is None:
            return

        if event.key() in {Qt.Key.Key_Space, Qt.Key.Key_Up, Qt.Key.Key_W}:
            self._state = jump_dinosaur(self._state)
            self._refresh_ui()
            event.accept()
            return
        if event.key() == Qt.Key.Key_P:
            self.toggle_pause()
            event.accept()
            return
        if event.key() == Qt.Key.Key_R:
            self.restart_game()
            event.accept()
            return

        super().keyPressEvent(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    _ = qapplication()  # analysis:ignore
    dlg = DinosaurDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
