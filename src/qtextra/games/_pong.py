"""Minimal Pong game dialog."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from qtpy.QtCore import QSize, Qt, QTimer
from qtpy.QtGui import QColor, QKeyEvent, QPainter, QPaintEvent, QPen
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config.theme import THEMES
from qtextra.widgets.qt_dialog import QtDialog

BOARD_WIDTH = 640
BOARD_HEIGHT = 360
PADDLE_WIDTH = 12
PADDLE_HEIGHT = 72
BALL_SIZE = 12
PADDLE_STEP = 20
AI_STEP = 16
BALL_SPEED_X = 5.0
BALL_SPEED_Y = 3.0
WIN_SCORE = 5
TICK_INTERVAL_MS = 16


@dataclass(frozen=True, slots=True)
class PongGameState:
    """Immutable Pong game state."""

    width: int
    height: int
    paddle_width: int
    paddle_height: int
    ball_size: int
    player_y: float
    ai_y: float
    ball_x: float
    ball_y: float
    ball_velocity_x: float
    ball_velocity_y: float
    player_score: int
    ai_score: int
    is_game_over: bool
    winner: str | None


def clamp_paddle(y_pos: float, board_height: int, paddle_height: int) -> float:
    """Clamp a paddle position to the visible board."""
    return max(0.0, min(y_pos, float(board_height - paddle_height)))


def _make_ball_velocity(rng: random.Random, *, toward_player: bool) -> tuple[float, float]:
    """Create a deterministic serve velocity."""
    vertical_speed = rng.choice((-BALL_SPEED_Y, -BALL_SPEED_Y + 1.0, BALL_SPEED_Y - 1.0, BALL_SPEED_Y))
    horizontal_speed = -BALL_SPEED_X if toward_player else BALL_SPEED_X
    return horizontal_speed, vertical_speed


def create_initial_state(
    *,
    width: int = BOARD_WIDTH,
    height: int = BOARD_HEIGHT,
    rng: random.Random | None = None,
) -> PongGameState:
    """Create a fresh Pong game state."""
    generator = rng if rng is not None else random.Random()
    player_y = (height - PADDLE_HEIGHT) / 2
    ai_y = (height - PADDLE_HEIGHT) / 2
    ball_velocity_x, ball_velocity_y = _make_ball_velocity(generator, toward_player=generator.choice((True, False)))
    return PongGameState(
        width=width,
        height=height,
        paddle_width=PADDLE_WIDTH,
        paddle_height=PADDLE_HEIGHT,
        ball_size=BALL_SIZE,
        player_y=player_y,
        ai_y=ai_y,
        ball_x=(width - BALL_SIZE) / 2,
        ball_y=(height - BALL_SIZE) / 2,
        ball_velocity_x=ball_velocity_x,
        ball_velocity_y=ball_velocity_y,
        player_score=0,
        ai_score=0,
        is_game_over=False,
        winner=None,
    )


def move_player_paddle(state: PongGameState, delta: float) -> PongGameState:
    """Move the player paddle up or down."""
    if state.is_game_over:
        return state
    player_y = clamp_paddle(state.player_y + delta, state.height, state.paddle_height)
    return replace(state, player_y=player_y)


def _reset_ball(state: PongGameState, rng: random.Random, *, toward_player: bool) -> PongGameState:
    """Reset the ball to the center after a point is scored."""
    ball_velocity_x, ball_velocity_y = _make_ball_velocity(rng, toward_player=toward_player)
    return replace(
        state,
        ball_x=(state.width - state.ball_size) / 2,
        ball_y=(state.height - state.ball_size) / 2,
        ball_velocity_x=ball_velocity_x,
        ball_velocity_y=ball_velocity_y,
    )


def advance_state(state: PongGameState, rng: random.Random) -> PongGameState:
    """Advance the Pong game by one tick."""
    if state.is_game_over:
        return state

    ball_x = state.ball_x + state.ball_velocity_x
    ball_y = state.ball_y + state.ball_velocity_y
    velocity_x = state.ball_velocity_x
    velocity_y = state.ball_velocity_y

    ai_center = state.ai_y + state.paddle_height / 2
    ball_center = ball_y + state.ball_size / 2
    if ai_center < ball_center - 4:
        ai_y = clamp_paddle(state.ai_y + AI_STEP, state.height, state.paddle_height)
    elif ai_center > ball_center + 4:
        ai_y = clamp_paddle(state.ai_y - AI_STEP, state.height, state.paddle_height)
    else:
        ai_y = state.ai_y

    if ball_y <= 0:
        ball_y = 0
        velocity_y = abs(velocity_y)
    elif ball_y + state.ball_size >= state.height:
        ball_y = state.height - state.ball_size
        velocity_y = -abs(velocity_y)

    player_x = 24
    ai_x = state.width - 24 - state.paddle_width

    if (
        velocity_x < 0
        and ball_x <= player_x + state.paddle_width
        and ball_y + state.ball_size >= state.player_y
        and ball_y <= state.player_y + state.paddle_height
    ):
        ball_x = player_x + state.paddle_width
        velocity_x = abs(velocity_x)
        offset = ((ball_y + state.ball_size / 2) - (state.player_y + state.paddle_height / 2)) / (
            state.paddle_height / 2
        )
        velocity_y = max(-6.0, min(6.0, velocity_y + offset * 1.5))
    elif (
        velocity_x > 0
        and ball_x + state.ball_size >= ai_x
        and ball_y + state.ball_size >= ai_y
        and ball_y <= ai_y + state.paddle_height
    ):
        ball_x = ai_x - state.ball_size
        velocity_x = -abs(velocity_x)
        offset = ((ball_y + state.ball_size / 2) - (ai_y + state.paddle_height / 2)) / (state.paddle_height / 2)
        velocity_y = max(-6.0, min(6.0, velocity_y + offset * 1.2))

    next_state = replace(
        state,
        ai_y=ai_y,
        ball_x=ball_x,
        ball_y=ball_y,
        ball_velocity_x=velocity_x,
        ball_velocity_y=velocity_y,
    )

    if next_state.ball_x + next_state.ball_size < 0:
        ai_score = next_state.ai_score + 1
        winner = "Computer" if ai_score >= WIN_SCORE else None
        next_state = replace(next_state, ai_score=ai_score, is_game_over=winner is not None, winner=winner)
        return _reset_ball(next_state, rng, toward_player=False) if winner is None else next_state
    if next_state.ball_x > next_state.width:
        player_score = next_state.player_score + 1
        winner = "Player" if player_score >= WIN_SCORE else None
        next_state = replace(
            next_state,
            player_score=player_score,
            is_game_over=winner is not None,
            winner=winner,
        )
        return _reset_ball(next_state, rng, toward_player=True) if winner is None else next_state

    return next_state


class PongBoardWidget(QWidget):
    """Paint the Pong board."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the board widget."""
        super().__init__(parent)
        self._state: PongGameState | None = None
        self.setMinimumSize(420, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self) -> QSize:
        """Return the preferred board size."""
        return QSize(540, 320)

    def set_state(self, state: PongGameState) -> None:
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
        board_background = background.darker(112) if THEMES.is_dark else background.lighter(104)
        line_color = QColor(THEMES.get_hex_color("primary"))
        paddle_color = QColor(THEMES.get_hex_color("success"))
        ball_color = QColor(THEMES.get_hex_color("warning"))
        overlay_color = QColor(THEMES.get_hex_color("error"))
        overlay_color.setAlpha(70)

        painter.fillRect(self.rect(), board_background)

        scale_x = self.width() / self._state.width
        scale_y = self.height() / self._state.height

        painter.setPen(QPen(line_color, 2))
        painter.drawLine(self.width() // 2, 0, self.width() // 2, self.height())

        paddle_width = round(self._state.paddle_width * scale_x)
        paddle_height = round(self._state.paddle_height * scale_y)
        player_x = round(24 * scale_x)
        ai_x = round((self._state.width - 24 - self._state.paddle_width) * scale_x)
        player_y = round(self._state.player_y * scale_y)
        ai_y = round(self._state.ai_y * scale_y)

        painter.fillRect(player_x, player_y, paddle_width, paddle_height, paddle_color)
        painter.fillRect(ai_x, ai_y, paddle_width, paddle_height, paddle_color)

        ball_x = round(self._state.ball_x * scale_x)
        ball_y = round(self._state.ball_y * scale_y)
        ball_size_x = max(1, round(self._state.ball_size * scale_x))
        ball_size_y = max(1, round(self._state.ball_size * scale_y))
        painter.fillRect(ball_x, ball_y, ball_size_x, ball_size_y, ball_color)

        if self._state.is_game_over:
            painter.fillRect(self.rect(), overlay_color)


class PongDialog(QtDialog):
    """Standalone dialog that hosts a minimal Pong game."""

    def __init__(self, parent: QWidget | None, *, rng: random.Random | None = None) -> None:
        """Initialize the Pong dialog."""
        self._rng = rng if rng is not None else random.Random()
        self._state = create_initial_state(rng=self._rng)
        self._is_paused = False
        super().__init__(parent, title="Pong")
        self.setMinimumSize(520, 440)
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

        self.board_widget = PongBoardWidget(self)
        self.instructions_label = hp.make_label(
            self,
            "Arrow keys or W/S move. Space pauses. R restarts.",
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

        delta = None
        if event.key() in {Qt.Key.Key_Up, Qt.Key.Key_W}:
            delta = -PADDLE_STEP
        elif event.key() in {Qt.Key.Key_Down, Qt.Key.Key_S}:
            delta = PADDLE_STEP
        elif event.key() == Qt.Key.Key_Space:
            self.toggle_pause()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_R:
            self.restart_game()
            event.accept()
            return

        if delta is not None:
            self._state = move_player_paddle(self._state, delta)
            self._refresh_ui()
            event.accept()
            return

        super().keyPressEvent(event)

    def restart_game(self) -> None:
        """Reset the game and start a new round."""
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
        self.score_label.setText(f"Score: {self._state.player_score} - {self._state.ai_score}")
        if self._state.is_game_over:
            status = f"{self._state.winner} wins"
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
    dlg = PongDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
