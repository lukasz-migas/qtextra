"""Tests for the circular countdown widget."""

from types import SimpleNamespace

import pytest
from qtpy.QtCore import QSize, Qt

from qtextra.widgets.qt_countdown import QtCircularCountdownWidget


@pytest.fixture
def clock(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("qtextra.widgets.qt_countdown.time", SimpleNamespace(monotonic=lambda: now[0]))
    return now


@pytest.fixture
def countdown(qtbot, clock):
    widget = QtCircularCountdownWidget(1000)
    qtbot.addWidget(widget)
    return widget


def test_start_pause_and_resume_preserve_remaining_time(countdown, clock):
    countdown.start()
    clock[0] += 0.4
    assert countdown.remaining_ms == pytest.approx(600, abs=1)
    countdown.pause()
    remaining = countdown.remaining_ms
    clock[0] += 5
    assert countdown.remaining_ms == remaining
    countdown.start()
    clock[0] += 0.2
    assert countdown.remaining_ms == pytest.approx(400, abs=1)


def test_start_while_running_does_not_restart(countdown, clock):
    countdown.start()
    clock[0] += 0.3
    countdown.start()
    assert countdown.remaining_ms == pytest.approx(700, abs=1)


def test_stop_and_set_duration_reset(countdown, clock):
    countdown.start()
    clock[0] += 0.5
    countdown.stop()
    assert countdown.remaining_ms == 1000
    countdown.start()
    countdown.set_duration(2000)
    assert countdown.remaining_ms == 2000
    assert not countdown._timer.isActive()


def test_negative_duration_rejected_without_changing_existing_countdown(countdown):
    with pytest.raises(ValueError):
        QtCircularCountdownWidget(-1)
    with pytest.raises(ValueError):
        countdown.set_duration(-1)
    assert countdown.remaining_ms == 1000


def test_expiry_once_and_restart(countdown, clock):
    expired = []
    countdown.evt_expired.connect(lambda: expired.append(True))
    countdown.start()
    clock[0] += 2
    countdown._on_tick()
    assert countdown.remaining_ms == 0
    assert not countdown._timer.isActive()
    countdown._on_tick()
    assert expired == [True]
    countdown.start()
    assert countdown.remaining_ms == 1000
    clock[0] += 1.1
    countdown._on_tick()
    assert expired == [True, True]


def test_pause_after_deadline_expires(countdown, clock):
    expired = []
    countdown.evt_expired.connect(lambda: expired.append(True))
    countdown.start()
    clock[0] += 2
    countdown.pause()
    countdown.pause()
    assert countdown.remaining_ms == 0
    assert expired == [True]


def test_zero_duration_expires_on_start(qtbot):
    widget = QtCircularCountdownWidget(0)
    qtbot.addWidget(widget)
    expired = []
    widget.evt_expired.connect(lambda: expired.append(True))
    widget.start()
    assert widget.remaining_ms == 0
    assert expired == [True]
    assert not widget._timer.isActive()


def test_auto_hide_and_restart(qtbot, clock):
    widget = QtCircularCountdownWidget(1000, auto_hide=True)
    qtbot.addWidget(widget)
    widget.show()
    widget.start()
    clock[0] += 2
    widget._on_tick()
    assert widget.isHidden()
    widget.start()
    assert not widget.isHidden()
    assert widget.remaining_ms == 1000


def test_no_auto_hide_by_default(qtbot, countdown, clock):
    countdown.show()
    countdown.start()
    clock[0] += 2
    countdown._on_tick()
    assert not countdown.isHidden()


def test_timer_expires_through_event_loop(qtbot):
    widget = QtCircularCountdownWidget(50)
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.evt_expired, timeout=2000):
        widget.start()
    assert widget.remaining_ms == 0


def test_small_and_large_rendering_with_optional_text(qtbot):
    plain = QtCircularCountdownWidget(65000)
    labelled = QtCircularCountdownWidget(65000, show_time=True)
    qtbot.addWidget(plain)
    qtbot.addWidget(labelled)
    assert labelled.sizeHint() == QSize(48, 48)

    plain.resize(20, 20)
    labelled.resize(20, 20)
    assert plain.grab().toImage() == labelled.grab().toImage()

    plain.resize(120, 120)
    labelled.resize(120, 120)
    assert plain.grab().toImage() != labelled.grab().toImage()

    plain.resize(20, 20)
    labelled.resize(20, 20)
    assert plain.grab().toImage() == labelled.grab().toImage()

    labelled.resize(120, 120)
    plain.resize(120, 120)
    assert plain.grab().toImage() != labelled.grab().toImage()


def test_small_ring_changes_as_time_passes(qtbot, countdown, clock):
    countdown.resize(20, 20)
    countdown.start()
    full = countdown.grab().toImage()
    clock[0] += 0.5
    half = countdown.grab().toImage()
    clock[0] += 1
    countdown._on_tick()
    empty = countdown.grab().toImage()
    assert full != half
    assert half != empty


def test_start_with_remaining_time_shows_partial_countdown(countdown, clock):
    countdown.start(remaining_ms=400)
    assert countdown.remaining_ms == 400
    clock[0] += 0.1
    assert countdown.remaining_ms == pytest.approx(300, abs=1)


def test_start_with_remaining_time_is_clamped_to_duration(countdown):
    countdown.start(remaining_ms=5000)
    assert countdown.remaining_ms == 1000


def test_left_click_emits_clicked(countdown, qtbot):
    countdown.resize(48, 48)
    with qtbot.waitSignal(countdown.evt_clicked, timeout=500):
        qtbot.mouseClick(countdown, Qt.MouseButton.LeftButton)
