"""Countdown timer widget that notifies users of upcoming updates or changes."""

from __future__ import annotations

import math
import time
from contextlib import suppress

from qtpy.QtCore import QRectF, QSize, Qt, QTimer, Signal
from qtpy.QtGui import QMouseEvent, QPainter, QPaintEvent, QPen
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


class QtCircularCountdownWidget(QWidget):
    """A circular countdown that can optionally display the remaining time.

    Parameters
    ----------
    duration_ms : int
        Countdown duration in milliseconds; must be non-negative.
    auto_hide : bool
        Hide the widget on expiry and show it when restarted.
    show_time : bool
        Display remaining time when it fits inside the ring.
    parent : QWidget or None
        Parent widget.

    Signals
    -------
    evt_expired : Signal
        Emitted once when a countdown reaches zero.
    evt_clicked : Signal
        Emitted when the widget is clicked with the left mouse button.
    """

    evt_expired = Signal()
    evt_clicked = Signal()

    def __init__(
        self,
        duration_ms: int,
        auto_hide: bool = False,
        show_time: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        from qtextra.config import THEMES

        super().__init__(parent)
        if duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        self._duration_ms = duration_ms
        self._remaining_ms = float(duration_ms)
        self._deadline: float | None = None
        self._expired = False
        self._auto_hidden = False
        self._auto_hide = auto_hide
        self._show_time = show_time
        self._themes = THEMES

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._on_tick)
        self._themes.evt_theme_changed.connect(self.update)

    def sizeHint(self) -> QSize:
        """Return a useful default size for the indicator."""
        return QSize(48, 48)

    @property
    def remaining_ms(self) -> int:
        """Return remaining time in milliseconds, rounded up."""
        if self._deadline is not None:
            return min(math.ceil(self._remaining_ms), max(0, math.ceil((self._deadline - time.monotonic()) * 1000)))
        return max(0, math.ceil(self._remaining_ms))

    def start(self, remaining_ms: int | None = None) -> None:
        """Start or resume the countdown; restart it after expiry.

        Parameters
        ----------
        remaining_ms : int or None
            Begin with this much time left (clamped to the duration) instead of resuming, e.g. when the
            tracked event was scheduled before the countdown started. Ignored while the countdown is running.
        """
        if self._deadline is not None:
            return
        if remaining_ms is not None:
            self._remaining_ms = float(min(max(0, remaining_ms), self._duration_ms))
            self._expired = False
        elif self._expired:
            self._remaining_ms = float(self._duration_ms)
            self._expired = False
        if self._auto_hidden:
            self._auto_hidden = False
            self.show()
        if self._remaining_ms <= 0:
            self._expire()
            return
        self._deadline = time.monotonic() + self._remaining_ms / 1000
        self._timer.start()
        self.update()

    def pause(self) -> None:
        """Pause the countdown, preserving the remaining time."""
        if self._deadline is None:
            return
        self._remaining_ms = max(0.0, (self._deadline - time.monotonic()) * 1000)
        self._deadline = None
        self._timer.stop()
        if self._remaining_ms <= 0:
            self._expire()
        else:
            self.update()

    def stop(self) -> None:
        """Stop the countdown and reset it to its full duration."""
        self._timer.stop()
        self._deadline = None
        self._remaining_ms = float(self._duration_ms)
        self._expired = False
        self.update()

    def set_duration(self, duration_ms: int) -> None:
        """Set a non-negative duration in milliseconds and reset the countdown."""
        if duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        self._duration_ms = duration_ms
        self.stop()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Emit `evt_clicked` after a left-button click inside the widget."""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.evt_clicked.emit()

    def _on_tick(self) -> None:
        if self._deadline is None:
            return
        if self.remaining_ms <= 0:
            self._expire()
        else:
            self.update()

    def _expire(self) -> None:
        self._timer.stop()
        self._deadline = None
        self._remaining_ms = 0.0
        self._expired = True
        if self._auto_hide:
            self.hide()
            self._auto_hidden = True
        self.update()
        self.evt_expired.emit()

    def _time_text(self, diameter: float, stroke: float) -> str:
        """Return text only when it fits inside the ring."""
        if not self._show_time or diameter <= 20:
            return ""
        seconds = math.ceil(self.remaining_ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        text = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
        metrics = self.fontMetrics()
        available = max(0.0, diameter - 2 * stroke - 4)
        if math.hypot(metrics.horizontalAdvance(text), metrics.height()) > available:
            return ""
        return text

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        """Paint the remaining fraction and optional time."""
        diameter = float(min(self.width(), self.height()))
        if diameter <= 0:
            return
        stroke = max(2.0, min(9.0, diameter * 0.18))
        inset = stroke / 2 + 1
        bounds = QRectF(
            (self.width() - diameter) / 2 + inset,
            (self.height() - diameter) / 2 + inset,
            max(0.0, diameter - 2 * inset),
            max(0.0, diameter - 2 * inset),
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track_pen = QPen(self._themes.get_qt_color("secondary"))
        track_pen.setWidthF(stroke)
        painter.setPen(track_pen)
        painter.drawEllipse(bounds)

        fraction = min(1.0, self.remaining_ms / self._duration_ms) if self._duration_ms else 0.0
        if fraction > 0:
            progress_pen = QPen(self._themes.get_qt_color("progress"))
            progress_pen.setWidthF(stroke)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)
            if fraction >= 1:
                painter.drawEllipse(bounds)
            else:
                start_angle = round((90 - 360 * (1 - fraction)) * 16)
                painter.drawArc(bounds, start_angle, -round(360 * fraction * 16))

        text = self._time_text(diameter, stroke)
        if text:
            painter.setPen(self._themes.get_qt_color("text"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


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
