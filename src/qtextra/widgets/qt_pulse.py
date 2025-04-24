"""Simple indicator widget."""

from __future__ import annotations

from qtpy.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Slot
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QGraphicsOpacityEffect, QSizePolicy, QWidget

INDICATOR_TYPES = {"success": "success", "warning": "warning", "active": "progress"}
DEFAULT_START_OPACITY = 1.0
DEFAULT_END_OPACITY = 0.2
DEFAULT_PULSE_RATE = 1000
DEFAULT_N_LOOPS = 5


class QtIndicator(QWidget):
    """Small indicator widget that flashes occasionally."""

    # states: success, warning, active, none
    START_OPACITY = DEFAULT_START_OPACITY
    END_OPACITY = DEFAULT_END_OPACITY
    PULSE_RATE = DEFAULT_PULSE_RATE
    N_LOOPS = DEFAULT_N_LOOPS

    def __init__(self, parent=None, max_size=None):
        super().__init__(parent=parent)
        self.setProperty("state", "none")
        self.setProperty("active", "False")
        if max_size:
            self.setMaximumSize(*max_size)
            self.setMinimumSize(*max_size)

        self.opacity = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity)
        self.opacity_anim = QPropertyAnimation(self.opacity, b"opacity", self)
        self.opacity_anim.currentLoopChanged.connect(self._loop_update)
        self.opacity_anim.finished.connect(self.stop_pulse)

        self.setContentsMargins(2, 2, 2, 2)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

    @property
    def state(self):
        """Get state."""
        return self.property("state")

    @state.setter
    def state(self, value: str):
        self.setProperty("state", value)

    @property
    def active(self):
        """Get active state."""
        return self.property("active")

    @active.setter
    def active(self, value: bool):
        self.setProperty("active", str(value))
        self.start_pulse() if value else self.stop_pulse()

    @Slot(int)
    def _loop_update(self, loop: int | None = None):
        """Reverse pulse direction for nicer visual effect."""
        if loop is None:
            loop = self.opacity_anim.currentLoop()
        start, end = (self.START_OPACITY, self.END_OPACITY) if loop % 2 == 0 else (self.END_OPACITY, self.START_OPACITY)
        self.opacity_anim.setStartValue(start)
        self.opacity_anim.setEndValue(end)

    def paintEvent(self, *args):
        """Paint event."""
        super().paintEvent(*args)
        # default paint
        width = self.rect().width()
        height = self.rect().height()
        pos = QPoint(width - int(width / 2) - 5, height - int(height / 4) - 5)

        paint = QPainter(self)
        pen = paint.pen()
        paint.setBrush(pen.brush())
        paint.drawEllipse(pos, int(width / 4), int(height / 4))

    def start_pulse(self):
        """Start pulsating."""
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.opacity_anim.setDuration(self.PULSE_RATE)
        self.opacity_anim.setStartValue(self.START_OPACITY)
        self.opacity_anim.setEndValue(self.END_OPACITY)
        self.opacity_anim.setLoopCount(self.N_LOOPS)
        self.opacity_anim.start()

    def stop_pulse(self):
        """Stop pulsating."""
        self.opacity_anim.stop()
        self.opacity.setOpacity(1.0)

    def temporary_pulse(self, duration: int = 1000, pulse: int = DEFAULT_PULSE_RATE):
        """Pulse for a short duration."""
        if self.opacity_anim.state() == QPropertyAnimation.State.Running:
            self.opacity_anim.stop()
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.opacity_anim.setDuration(pulse)
        self.opacity_anim.setStartValue(self.START_OPACITY)
        self.opacity_anim.setEndValue(self.END_OPACITY)
        self.opacity_anim.setLoopCount(max(1, round(duration / pulse)))
        self.opacity_anim.finished.connect(self.hide)
        self.opacity_anim.start()
        self.show()


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe(False)
        frame.setMinimumSize(600, 600)

        btn2 = QtIndicator(parent=frame)
        btn2.setMaximumSize(16, 16)
        btn2.state = "warning"
        btn2.start_pulse()
        ha.addWidget(btn2)

        btn2 = QtIndicator(parent=frame)
        btn2.setMaximumSize(20, 20)
        btn2.state = "success"
        btn2.start_pulse()
        ha.addWidget(btn2)

        btn2 = QtIndicator(parent=frame)
        btn2.setMaximumSize(80, 80)
        btn2.state = "active"
        btn2.start_pulse()
        ha.addWidget(btn2)

        frame.show()
        sys.exit(app.exec_())

    _main()
