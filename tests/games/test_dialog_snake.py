"""Tests for the Snake dialog and game logic."""

from __future__ import annotations

import random

from qtpy.QtCore import Qt

from qtextra.games._snake import (
    GridPoint,
    SnakeDialog,
    SnakeDirection,
    SnakeGameState,
    advance_state,
    change_direction,
    create_initial_state,
    spawn_food,
)


def test_create_initial_state_places_food_off_snake() -> None:
    rng = random.Random(0)

    state = create_initial_state(rng=rng)

    assert len(state.snake) == 3
    assert state.food is not None
    assert state.food not in state.snake
    assert state.score == 0
    assert state.direction is SnakeDirection.RIGHT
    assert state.is_game_over is False


def test_advance_state_moves_snake_one_step() -> None:
    state = SnakeGameState(
        width=8,
        height=8,
        snake=(GridPoint(4, 4), GridPoint(3, 4), GridPoint(2, 4)),
        food=GridPoint(0, 0),
        score=0,
        direction=SnakeDirection.RIGHT,
        last_direction=SnakeDirection.RIGHT,
        has_started=False,
        is_game_over=False,
    )

    result = advance_state(state, random.Random(0))

    assert result.snake == (GridPoint(5, 4), GridPoint(4, 4), GridPoint(3, 4))
    assert result.last_direction is SnakeDirection.RIGHT
    assert result.has_started is True


def test_change_direction_allows_each_non_reverse_move() -> None:
    state = SnakeGameState(
        width=8,
        height=8,
        snake=(GridPoint(4, 4), GridPoint(3, 4), GridPoint(2, 4)),
        food=GridPoint(1, 1),
        score=0,
        direction=SnakeDirection.RIGHT,
        last_direction=SnakeDirection.RIGHT,
        has_started=False,
        is_game_over=False,
    )

    assert change_direction(state, SnakeDirection.UP).direction is SnakeDirection.UP
    assert change_direction(state, SnakeDirection.DOWN).direction is SnakeDirection.DOWN
    assert change_direction(state, SnakeDirection.RIGHT).direction is SnakeDirection.RIGHT


def test_change_direction_rejects_reverse_after_start() -> None:
    state = SnakeGameState(
        width=8,
        height=8,
        snake=(GridPoint(4, 4), GridPoint(3, 4), GridPoint(2, 4)),
        food=GridPoint(1, 1),
        score=0,
        direction=SnakeDirection.RIGHT,
        last_direction=SnakeDirection.RIGHT,
        has_started=True,
        is_game_over=False,
    )

    result = change_direction(state, SnakeDirection.LEFT)

    assert result.direction is SnakeDirection.RIGHT


def test_advance_state_grows_snake_and_scores() -> None:
    state = SnakeGameState(
        width=8,
        height=8,
        snake=(GridPoint(4, 4), GridPoint(3, 4), GridPoint(2, 4)),
        food=GridPoint(5, 4),
        score=0,
        direction=SnakeDirection.RIGHT,
        last_direction=SnakeDirection.RIGHT,
        has_started=True,
        is_game_over=False,
    )

    result = advance_state(state, random.Random(0))

    assert result.score == 1
    assert len(result.snake) == 4
    assert result.snake[0] == GridPoint(5, 4)
    assert result.food is not None
    assert result.food not in result.snake


def test_advance_state_sets_game_over_on_wall_collision() -> None:
    state = SnakeGameState(
        width=4,
        height=4,
        snake=(GridPoint(3, 1), GridPoint(2, 1), GridPoint(1, 1)),
        food=GridPoint(0, 0),
        score=0,
        direction=SnakeDirection.RIGHT,
        last_direction=SnakeDirection.RIGHT,
        has_started=True,
        is_game_over=False,
    )

    result = advance_state(state, random.Random(0))

    assert result.is_game_over is True


def test_advance_state_sets_game_over_on_self_collision() -> None:
    state = SnakeGameState(
        width=6,
        height=6,
        snake=(
            GridPoint(2, 2),
            GridPoint(2, 3),
            GridPoint(1, 3),
            GridPoint(1, 2),
            GridPoint(1, 1),
            GridPoint(2, 1),
        ),
        food=GridPoint(5, 5),
        score=0,
        direction=SnakeDirection.DOWN,
        last_direction=SnakeDirection.RIGHT,
        has_started=True,
        is_game_over=False,
    )

    result = advance_state(state, random.Random(0))

    assert result.is_game_over is True


def test_spawn_food_avoids_snake_cells() -> None:
    snake = (
        GridPoint(0, 0),
        GridPoint(1, 0),
        GridPoint(2, 0),
        GridPoint(0, 1),
    )

    for seed in range(10):
        food = spawn_food(4, 4, snake, random.Random(seed))
        assert food is not None
        assert food not in snake


def test_snake_dialog_constructs(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, SnakeDialog(None, tick_interval_ms=1_000))

    assert widget.windowTitle() == "Snake Game"
    assert widget.score_label.text() == "Score: 0"
    assert widget.status_label.text() == "Running"
    assert widget.restart_button.isEnabled()


def test_snake_dialog_pause_toggles_timer_progress(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, SnakeDialog(None, tick_interval_ms=20, rng=random.Random(0)))
    start_head = widget._state.snake[0]

    qtbot.wait(60)
    moved_head = widget._state.snake[0]
    assert moved_head != start_head

    qtbot.keyClick(widget, Qt.Key.Key_Space)
    paused_head = widget._state.snake[0]
    qtbot.wait(60)
    assert widget.status_label.text() == "Paused"
    assert widget._state.snake[0] == paused_head

    qtbot.keyClick(widget, Qt.Key.Key_Space)
    qtbot.wait(60)
    assert widget.status_label.text() == "Running"
    assert widget._state.snake[0] != paused_head


def test_snake_dialog_restart_resets_state_after_game_over(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, SnakeDialog(None, width=4, height=4, tick_interval_ms=1_000, rng=random.Random(0)))
    widget._state = SnakeGameState(
        width=4,
        height=4,
        snake=(GridPoint(3, 1), GridPoint(2, 1), GridPoint(1, 1)),
        food=GridPoint(0, 0),
        score=2,
        direction=SnakeDirection.RIGHT,
        last_direction=SnakeDirection.RIGHT,
        has_started=True,
        is_game_over=False,
    )
    widget.advance_game()

    assert widget.status_label.text() == "Game over"

    qtbot.keyClick(widget, Qt.Key.Key_R)

    assert widget.status_label.text() == "Running"
    assert widget.score_label.text() == "Score: 0"
    assert len(widget._state.snake) == 3
    assert widget._state.is_game_over is False
