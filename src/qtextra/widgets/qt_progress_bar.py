"""Loading bar."""

from qtpy.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QProgressBar


class QtLineProgressBar(QProgressBar):
    """Thin progress bar."""

    Direction = 0
    Height = 2
    Color = QColor("#00d989")
    FailedColor = QColor("#ed3814")

    # Enum attributes
    TOP = 0
    BOTTOM = 1
    Instances = {}

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, parent=parent, **kwargs)
        if parent:
            parent.installEventFilter(self)
        self._height = None  # height of the widget
        self._color = None  # color of the progress bar
        self._failed_color = None  # color when progress had failed
        self._direction = None  # direction
        self._alpha = 255  # transparency
        self.is_error = False  # flag to indicate whether progress had failed
        self.setOrientation(Qt.Orientation.Horizontal)
        self.setTextVisible(False)
        self.animation = QPropertyAnimation(self, b"alpha", self, loopCount=1, duration=1000)
        self.animation.setEasingCurve(QEasingCurve.Type.SineCurve)
        self.animation.setStartValue(0)
        self.animation.setEndValue(255)
        self.Instances[self] = self

    @property
    def alpha(self):
        """Return alpha."""
        return self._alpha

    @alpha.setter
    def alpha(self, alpha):
        self._alpha = alpha
        QProgressBar.update(self)

    def paintEvent(self, _):
        """Paint event."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        # background color
        painter.fillRect(self.rect(), Qt.transparent)
        # progress
        ratio = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        width = self.rect().width() * ratio
        if self.is_error:
            color = QColor(self._failed_color or QtLineProgressBar.FailedColor)
        else:
            color = QColor(self._color or QtLineProgressBar.Color)
        color.setAlpha(self._alpha)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, width, self.height()), 2, 2)

    def eventFilter(self, obj, event):
        """Filter events."""
        if event.type() == event.Resize:
            # resize event
            widget = QtLineProgressBar.Instances.get(obj, None)
            if widget:
                direction = widget._direction or QtLineProgressBar.Direction
                height = widget._height or QtLineProgressBar.Height
                widget.setGeometry(
                    0, 0 if direction == QtLineProgressBar.TOP else obj.height() - height, obj.width(), height
                )
        return super().eventFilter(obj, event)

    def start(self, minimum=0, maximum=100, height=None, direction=None, color=None, failed_color=None):
        """Create a loading bar.

        Parameters
        ----------
        minimum : int
            Lower step value.
        maximum : int
            Upper step value.
        height : int
            Height of the progress bar.
        direction : int
            Progress bar position
        color : str
            Success color
        failed_color : str
            Fail color.
        """
        self._height = height
        self._color = color
        self._failed_color = failed_color
        self._direction = direction
        self.setRange(minimum, maximum)
        self.setValue(minimum)
        direction = self._direction or QtLineProgressBar.Direction
        height = self._height or QtLineProgressBar.Height
        self.setGeometry(
            0,
            0 if direction == QtLineProgressBar.TOP else self.parent().height() - height,
            self.parent().width(),
            height,
        )

    def finish(self):
        """Finish."""
        self._alpha = 255
        self.is_error = False
        self.setValue(self.maximum())
        self.animation.start()

    def error(self):
        """Raise error."""
        self._alpha = 255
        self.is_error = True
        self.setValue(self.maximum())
        self.animation.start()

    def update_value(self, value):
        """Update."""
        self._alpha = 255
        self.is_error = False
        self.show()
        self.setValue(value)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe(False)
        frame.setMinimumSize(600, 600)

        widget = QtLineProgressBar(parent=frame)
        widget.start(height=50)
        widget.update_value(50)
        ha.addWidget(widget)

        widget = QtLineProgressBar(parent=frame)
        widget.start(height=1, direction=QtLineProgressBar.TOP)
        widget.update_value(30)
        ha.addWidget(widget)

        widget = QtLineProgressBar(parent=frame)
        widget.start(height=1, direction=QtLineProgressBar.TOP)
        widget.update_value(76)
        ha.addWidget(widget)

        frame.show()
        sys.exit(app.exec_())

    _main()
