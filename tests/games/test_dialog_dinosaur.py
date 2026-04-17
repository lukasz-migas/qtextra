"""Tests for the dinosaur dialog and game logic."""

from __future__ import annotations

import random

import pytest
from qtpy.QtCore import Qt

from qtextra.games._dinosaur import (
    DINO_HEIGHT,
    DinosaurDialog,
    DinosaurGameState,
    Obstacle,
    advance_state,
    create_initial_state,
    jump_dinosaur,
)


def test_create_initial_state_sets_grounded_dinosaur() -> None:
    state = create_initial_state(rng=random.Random(0))

    assert state.score == 0
    assert state.obstacles == ()
    assert state.dino_y == float(state.ground_y - DINO_HEIGHT)


def test_jump_dinosaur_sets_vertical_velocity() -> None:
    state = create_initial_state(rng=random.Random(0))

    result = jump_dinosaur(state)

    assert result.vertical_velocity < 0
    assert result.has_started is True


def test_advance_state_moves_obstacles_and_scores() -> None:
    state = DinosaurGameState(
        width=720,
        height=240,
        ground_y=204,
        dino_x=80,
        dino_width=36,
        dino_height=DINO_HEIGHT,
        dino_y=162.0,
        vertical_velocity=0.0,
        obstacles=(Obstacle(x=300.0, width=20, height=30),),
        score=0,
        speed=8.0,
        spawn_cooldown=10,
        is_game_over=False,
        has_started=False,
    )

    result = advance_state(state, random.Random(0))

    assert result.score == 1
    assert result.obstacles[0].x < state.obstacles[0].x


def test_advance_state_spawns_obstacle_when_cooldown_expires() -> None:
    state = create_initial_state(rng=random.Random(0))
    state = DinosaurGameState(
        width=state.width,
        height=state.height,
        ground_y=state.ground_y,
        dino_x=state.dino_x,
        dino_width=state.dino_width,
        dino_height=state.dino_height,
        dino_y=state.dino_y,
        vertical_velocity=state.vertical_velocity,
        obstacles=(),
        score=0,
        speed=state.speed,
        spawn_cooldown=1,
        is_game_over=False,
        has_started=False,
    )

    result = advance_state(state, random.Random(0))

    assert len(result.obstacles) == 1


def test_advance_state_sets_game_over_on_collision() -> None:
    state = DinosaurGameState(
        width=720,
        height=240,
        ground_y=204,
        dino_x=80,
        dino_width=36,
        dino_height=DINO_HEIGHT,
        dino_y=162.0,
        vertical_velocity=0.0,
        obstacles=(Obstacle(x=90.0, width=22, height=42),),
        score=0,
        speed=8.0,
        spawn_cooldown=10,
        is_game_over=False,
        has_started=False,
    )

    result = advance_state(state, random.Random(0))

    assert result.is_game_over is True


def test_dinosaur_dialog_constructs(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, DinosaurDialog(None, rng=random.Random(0)))

    assert widget.windowTitle() == "Dinosaur Game"
    assert widget.score_label.text() == "Score: 0"
    assert widget.status_label.text() == "Running"


@pytest.mark.xfail()
def test_dinosaur_dialog_pause_stops_progress(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, DinosaurDialog(None, rng=random.Random(0)))
    start_score = widget._state.score

    qtbot.wait(80)
    moved_score = widget._state.score
    assert moved_score > start_score

    qtbot.keyClick(widget, Qt.Key.Key_P)
    paused_score = widget._state.score
    qtbot.wait(80)
    assert widget.status_label.text() == "Paused"
    assert widget._state.score == paused_score


def test_dinosaur_dialog_restart_resets_score(qtbot, add_qt_widget) -> None:
    widget = add_qt_widget(qtbot, DinosaurDialog(None, rng=random.Random(0)))
    widget._state = DinosaurGameState(
        width=720,
        height=240,
        ground_y=204,
        dino_x=80,
        dino_width=36,
        dino_height=DINO_HEIGHT,
        dino_y=162.0,
        vertical_velocity=0.0,
        obstacles=(Obstacle(x=90.0, width=22, height=42),),
        score=42,
        speed=8.0,
        spawn_cooldown=10,
        is_game_over=True,
        has_started=True,
    )
    widget._refresh_ui()

    qtbot.keyClick(widget, Qt.Key.Key_R)

    assert widget.score_label.text() == "Score: 0"
    assert widget.status_label.text() == "Running"
    assert widget._state.is_game_over is False
