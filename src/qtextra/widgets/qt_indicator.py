"""Simple indicator widget."""

from qtpy.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Slot
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QGraphicsOpacityEffect, QSizePolicy, QWidget

INDICATOR_TYPES = {"success": "success", "warning": "warning", "active": "progress"}


class QtIndicator(QWidget):
    """Small indicator widget that flashes occasionally."""

    # states: success, warning, active, none
    START_OPACITY = 1.0
    END_OPACITY = 0.2
    PULSE_RATE = 1000
    N_LOOPS = 5

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
    def _loop_update(self, loop: int):
        """Reverse pulse direction for nicer visual effect."""
        start, end = (self.START_OPACITY, self.END_OPACITY) if loop % 2 == 0 else (self.END_OPACITY, self.START_OPACITY)
        self.opacity_anim.setStartValue(start)
        self.opacity_anim.setEndValue(end)

    def paintEvent(self, *args):
        """Paint event."""
        super().paintEvent(*args)
        # default paint
        width = self.rect().width()
        height = self.rect().height()
        pos = QPoint(width - (width / 2) - 5, height - (height / 4) - 5)

        paint = QPainter(self)
        pen = paint.pen()
        paint.setBrush(pen.brush())
        paint.drawEllipse(pos, width / 4, height / 4)

    def start_pulse(self):
        """Start pulsating."""
        self.opacity_anim.setEasingCurve(QEasingCurve.Linear)
        self.opacity_anim.setDuration(self.PULSE_RATE)
        self.opacity_anim.setStartValue(self.START_OPACITY)
        self.opacity_anim.setEndValue(self.END_OPACITY)
        self.opacity_anim.setLoopCount(self.N_LOOPS)
        self.opacity_anim.start()

    def stop_pulse(self):
        """Stop pulsating."""
        self.opacity_anim.stop()
        self.opacity.setOpacity(1.0)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qmain, theme_toggle_btn

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)
        ha.addWidget(theme_toggle_btn(frame))

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
