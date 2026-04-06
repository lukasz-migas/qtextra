"""Countdown timer widget that notifies users of upcoming updates or changes."""

from __future__ import annotations

from contextlib import suppress

from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtWidgets import QHBoxLayout, QProgressBar, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp


def _format_remaining(seconds: float) -> str:
    """Return a human-readable string for the remaining time."""
    seconds = max(0, int(seconds))
    if seconds == 0:
        return "now"

    parts: list[str] = []
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes and not days:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds and not days and not hours:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " and ".join(parts[:2]) if len(parts) >= 2 else parts[0]


class QtCountdownWidget(QWidget):
    """Widget that displays remaining time until an upcoming event.

    Shows a label with a human-readable countdown and a thin progress bar
    that fills as the deadline approaches.

    Signals
    -------
    evt_expired : Signal
        Emitted when the countdown reaches zero.
    evt_tick : Signal(float)
        Emitted on each timer tick with the remaining seconds.
    """

    evt_expired: Signal = Signal()
    evt_tick: Signal = Signal(float)

    def __init__(
        self,
        duration_seconds: float,
        message: str = "Update in",
        show_label: bool = True,
        parent: QWidget | None = None,
        tick_interval_ms: int = 50,
    ):
        super().__init__(parent)
        self._total_seconds = float(duration_seconds)
        self._remaining_seconds = float(duration_seconds)
        self._tick_interval_ms = tick_interval_ms
        self._message = message

        self._timer = QTimer(self)
        self._timer.setInterval(self._tick_interval_ms)
        self._timer.timeout.connect(self._on_tick)

        self._make_ui(show_label)
        self._update_display()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _make_ui(self, show_label: bool) -> None:
        self._label = hp.make_label(
            self,
            text="",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._label.setVisible(show_label)

        self._progress = QProgressBar(self)
        self._progress.setObjectName("progress_timer")
        self._progress.setTextVisible(False)
        self._progress.setMinimum(0)
        self._progress.setMaximum(1000)
        self._progress.setValue(0)
        self._progress.setMaximumHeight(4)
        self._progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._label)
        layout.addWidget(self._progress)

    def start(self) -> None:
        """Start the countdown."""
        self._timer.start()

    def stop(self) -> None:
        """Stop the countdown without resetting."""
        self._timer.stop()

    def reset(self, duration_seconds: float | None = None) -> None:
        """Reset the countdown, optionally with a new duration."""
        self._timer.stop()
        if duration_seconds is not None:
            self._total_seconds = float(duration_seconds)
        self._remaining_seconds = self._total_seconds
        self._update_display()

    @property
    def message(self) -> str:
        """Prefix message shown before the remaining time."""
        return self._message

    @message.setter
    def message(self, value: str) -> None:
        self._message = value
        self._update_display()

    @property
    def label_visible(self) -> bool:
        """Whether the text label is visible.

        Uses ``not isHidden()`` so it reflects the explicit show/hide state
        regardless of whether the parent widget has been shown yet.
        """
        return not self._label.isHidden()

    @label_visible.setter
    def label_visible(self, value: bool) -> None:
        self._label.setVisible(value)

    @property
    def remaining_seconds(self) -> float:
        """Remaining time in seconds."""
        return self._remaining_seconds

    def _on_tick(self) -> None:
        self._remaining_seconds = max(0.0, self._remaining_seconds - self._tick_interval_ms / 1000.0)
        self._update_display()
        self.evt_tick.emit(self._remaining_seconds)
        if self._remaining_seconds <= 0:
            self._timer.stop()
            self.evt_expired.emit()

    def _update_display(self) -> None:
        with suppress(RuntimeError):
            human = _format_remaining(self._remaining_seconds)
            self._label.setText(f"{self._message} {human}")

            if self._total_seconds > 0:
                elapsed_fraction = 1.0 - self._remaining_seconds / self._total_seconds
                self._progress.setValue(int(elapsed_fraction * 1000))
            else:
                self._progress.setValue(1000)


if __name__ == "__main__":  # pragma: no cover

    def _main() -> None:
        import sys

        from qtextra.utils.dev import qframe

        app, frame, layout = qframe(False)
        frame.setMinimumSize(400, 120)

        countdown = QtCountdownWidget(duration_seconds=30, tick_interval_ms=50, message="Update in", parent=frame)
        countdown.evt_expired.connect(lambda: print("Countdown expired!"))

        btn_start = hp.make_btn(frame, "Start")
        btn_start.clicked.connect(countdown.start)
        btn_stop = hp.make_btn(frame, "Stop")
        btn_stop.clicked.connect(countdown.stop)
        btn_reset = hp.make_btn(frame, "Reset (60s)")
        btn_reset.clicked.connect(lambda: countdown.reset(60))
        btn_toggle = hp.make_btn(frame, "Toggle label")
        btn_toggle.clicked.connect(lambda: setattr(countdown, "label_visible", not countdown.label_visible))

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_start)
        btn_row.addWidget(btn_stop)
        btn_row.addWidget(btn_reset)
        btn_row.addWidget(btn_toggle)

        layout.addWidget(countdown)
        layout.addLayout(btn_row)

        countdown.start()
        frame.show()
        sys.exit(app.exec_())

    _main()
