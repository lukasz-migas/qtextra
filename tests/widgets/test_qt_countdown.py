"""Tests for QtCountdownWidget."""

import pytest

from qtextra.widgets.qt_countdown import QtCountdownWidget, _format_remaining

# ---------------------------------------------------------------------------
# _format_remaining unit tests (no Qt needed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "now"),
        (1, "1 second"),
        (59, "59 seconds"),
        (60, "1 minute"),
        (90, "1 minute and 30 seconds"),
        (3600, "1 hour"),
        (3661, "1 hour and 1 minute"),
        (7200, "2 hours"),
        (86400, "1 day"),
        (90061, "1 day and 1 hour"),
        (172800, "2 days"),
    ],
)
def test_format_remaining(seconds, expected):
    assert _format_remaining(seconds) == expected


def test_format_remaining_negative_clamps_to_now():
    assert _format_remaining(-10) == "now"


# ---------------------------------------------------------------------------
# Widget tests
# ---------------------------------------------------------------------------


@pytest.fixture
def countdown(qtbot):
    widget = QtCountdownWidget(duration_seconds=10, tick_interval_ms=100)
    qtbot.addWidget(widget)
    return widget


def test_initial_state(countdown):
    assert countdown.remaining_seconds == pytest.approx(10.0)
    assert countdown.label_visible is True
    assert "10" in countdown._label.text() or "second" in countdown._label.text()
    assert countdown._progress.value() == 0


def test_progress_bar_fills_as_time_elapses(qtbot, countdown):
    countdown.start()
    qtbot.wait(250)
    countdown.stop()
    assert countdown._progress.value() > 0


def test_remaining_seconds_decrease_after_start(qtbot, countdown):
    countdown.start()
    qtbot.wait(250)
    countdown.stop()
    assert countdown.remaining_seconds < 10.0


def test_stop_halts_countdown(qtbot, countdown):
    countdown.start()
    qtbot.wait(200)
    countdown.stop()
    remaining_at_stop = countdown.remaining_seconds
    qtbot.wait(200)
    assert countdown.remaining_seconds == pytest.approx(remaining_at_stop)


def test_reset_restores_full_duration(qtbot, countdown):
    countdown.start()
    qtbot.wait(200)
    countdown.stop()
    countdown.reset()
    assert countdown.remaining_seconds == pytest.approx(10.0)
    assert countdown._progress.value() == 0


def test_reset_with_new_duration(countdown):
    countdown.reset(duration_seconds=60)
    assert countdown.remaining_seconds == pytest.approx(60.0)
    assert countdown._progress.value() == 0


def test_label_toggle(countdown):
    assert countdown.label_visible is True
    countdown.label_visible = False
    assert countdown.label_visible is False
    countdown.label_visible = True
    assert countdown.label_visible is True


def test_message_property_updates_label(countdown):
    countdown.message = "Restart in"
    assert "Restart in" in countdown._label.text()


def test_evt_expired_emitted(qtbot):
    widget = QtCountdownWidget(duration_seconds=0.1, tick_interval_ms=50)
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.evt_expired, timeout=1000):
        widget.start()


def test_evt_tick_emitted(qtbot):
    widget = QtCountdownWidget(duration_seconds=10, tick_interval_ms=50)
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.evt_tick, timeout=500):
        widget.start()
    widget.stop()


def test_timer_stops_at_zero(qtbot):
    widget = QtCountdownWidget(duration_seconds=0.2, tick_interval_ms=50)
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.evt_expired, timeout=2000):
        widget.start()

    assert widget.remaining_seconds == pytest.approx(0.0)
    assert not widget._timer.isActive()


def test_progress_bar_at_maximum_when_expired(qtbot):
    widget = QtCountdownWidget(duration_seconds=0.2, tick_interval_ms=50)
    qtbot.addWidget(widget)

    # Capture the progress value inside the signal slot (synchronous w.r.t. emit)
    captured = []
    widget.evt_expired.connect(lambda: captured.append(widget._progress.value()))

    with qtbot.waitSignal(widget.evt_expired, timeout=2000):
        widget.start()

    assert captured == [widget._progress.maximum()]
    assert widget.remaining_seconds == pytest.approx(0.0)
