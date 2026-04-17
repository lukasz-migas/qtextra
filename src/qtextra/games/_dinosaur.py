"""Minimal Chrome-style dinosaur game dialog."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from qtpy.QtCore import QSize, Qt, QTimer
from qtpy.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent, QPen
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config.theme import THEMES
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


class DinosaurBoardWidget(QWidget):
    """Paint the dinosaur runner board."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the board widget."""
        super().__init__(parent)
        self._state: DinosaurGameState | None = None
        self.setMinimumSize(480, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self) -> QSize:
        """Return the preferred board size."""
        return QSize(560, 240)

    def set_state(self, state: DinosaurGameState) -> None:
        """Store state and schedule repaint."""
        self._state = state
        self.update()

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
        overlay_color = QColor(THEMES.get_hex_color("error"))
        overlay_color.setAlpha(70)

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
            painter.fillRect(self.rect(), overlay_color)


class DinosaurDialog(QtDialog):
    """Standalone dialog that hosts a minimal dinosaur runner."""

    def __init__(self, parent: QWidget | None, *, rng: random.Random | None = None) -> None:
        """Initialize the dinosaur dialog."""
        self._rng = rng if rng is not None else random.Random()
        self._state = create_initial_state(rng=self._rng)
        self._is_paused = False
        super().__init__(parent, title="Dinosaur Game")
        self.setMinimumSize(560, 400)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.timer = QTimer(self)
        self.timer.setInterval(TICK_INTERVAL_MS)
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

        self.board_widget = DinosaurBoardWidget(self)
        self.instructions_label = hp.make_label(
            self,
            "Space, Up, or W jumps. P pauses. R restarts.",
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

    def restart_game(self) -> None:
        """Reset the game and start a new run."""
        self._state = create_initial_state(rng=self._rng)
        self._is_paused = False
        self.timer.start()
        self._refresh_ui()
        self.setFocus()

    def toggle_pause(self) -> None:
        """Pause or resume the game."""
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
        """Update labels and board state."""
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
    dlg = DinosaurDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
