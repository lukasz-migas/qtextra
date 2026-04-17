"""Tests for the Pong dialog and game logic."""

from __future__ import annotations

import random

from qtpy.QtCore import Qt

from qtextra.games._pong import (
    BALL_SIZE,
    PADDLE_HEIGHT,
    PongDialog,
    PongGameState,
    advance_state,
    clamp_paddle,
    create_initial_state,
    move_player_paddle,
)


def test_create_initial_state_sets_scores_and_ball() -> None:
    state = create_initial_state(rng=random.Random(0))

    assert state.player_score == 0
    assert state.ai_score == 0
    assert state.winner is None
    assert state.ball_velocity_x != 0


def test_clamp_paddle_keeps_paddle_inside_board() -> None:
    assert clamp_paddle(-10, 200, PADDLE_HEIGHT) == 0.0
    assert clamp_paddle(500, 200, PADDLE_HEIGHT) == float(200 - PADDLE_HEIGHT)


def test_move_player_paddle_updates_position() -> None:
    state = create_initial_state(rng=random.Random(0))

    result = move_player_paddle(state, -20)

    assert result.player_y < state.player_y


def test_advance_state_bounces_off_top_wall() -> None:
    state = PongGameState(
        width=640,
        height=360,
        paddle_width=12,
        paddle_height=PADDLE_HEIGHT,
        ball_size=BALL_SIZE,
        player_y=140.0,
        ai_y=140.0,
        ball_x=200.0,
        ball_y=0.0,
        ball_velocity_x=5.0,
        ball_velocity_y=-3.0,
        player_score=0,
        ai_score=0,
        is_game_over=False,
        winner=None,
    )

    result = advance_state(state, random.Random(0))

    assert result.ball_velocity_y > 0


def test_advance_state_bounces_off_player_paddle() -> None:
    state = PongGameState(
        width=640,
        height=360,
        paddle_width=12,
        paddle_height=PADDLE_HEIGHT,
        ball_size=BALL_SIZE,
        player_y=140.0,
        ai_y=140.0,
        ball_x=38.0,
        ball_y=160.0,
        ball_velocity_x=-5.0,
        ball_velocity_y=0.0,
        player_score=0,
        ai_score=0,
        is_game_over=False,
        winner=None,
    )

    result = advance_state(state, random.Random(0))

    assert result.ball_velocity_x > 0


def test_advance_state_scores_point_for_player() -> None:
    state = PongGameState(
        width=640,
        height=360,
        paddle_width=12,
        paddle_height=PADDLE_HEIGHT,
        ball_size=BALL_SIZE,
        player_y=140.0,
        ai_y=0.0,
        ball_x=641.0,
        ball_y=320.0,
        ball_velocity_x=5.0,
        ball_velocity_y=0.0,
        player_score=0,
        ai_score=0,
        is_game_over=False,
        winner=None,
    )

    result = advance_state(state, random.Random(0))

    assert result.player_score == 1
    assert result.ai_score == 0


def test_pong_dialog_constructs(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, PongDialog(None, rng=random.Random(0)))

    assert widget.windowTitle() == "Pong"
    assert widget.score_label.text() == "Score: 0 - 0"
    assert widget.status_label.text() == "Running"


def test_pong_dialog_pause_stops_ball_progress(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, PongDialog(None, rng=random.Random(0)))
    start_x = widget._state.ball_x

    qtbot.wait(60)
    moved_x = widget._state.ball_x
    assert moved_x != start_x

    qtbot.keyClick(widget, Qt.Key.Key_Space)
    paused_x = widget._state.ball_x
    qtbot.wait(60)
    assert widget.status_label.text() == "Paused"
    assert widget._state.ball_x == paused_x


def test_pong_dialog_restart_resets_score(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, PongDialog(None, rng=random.Random(0)))
    widget._state = PongGameState(
        width=640,
        height=360,
        paddle_width=12,
        paddle_height=PADDLE_HEIGHT,
        ball_size=BALL_SIZE,
        player_y=140.0,
        ai_y=140.0,
        ball_x=320.0,
        ball_y=120.0,
        ball_velocity_x=5.0,
        ball_velocity_y=0.0,
        player_score=4,
        ai_score=5,
        is_game_over=True,
        winner="Computer",
    )
    widget._refresh_ui()

    qtbot.keyClick(widget, Qt.Key.Key_R)

    assert widget.score_label.text() == "Score: 0 - 0"
    assert widget.status_label.text() == "Running"
    assert widget._state.player_score == 0
    assert widget._state.ai_score == 0
