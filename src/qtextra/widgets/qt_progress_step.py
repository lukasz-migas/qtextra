"""Progress bar."""

from qtpy.QtCore import Property, QPoint, QRect, QSize, Qt, QVariantAnimation, Signal
from qtpy.QtGui import QFontMetrics, QPainter, QPen
from qtpy.QtWidgets import QWidget

from qtextra.config import THEMES

# TODO: if the step description is multi-line, it will not be displayed properly


class QtStepProgressBar(QWidget):
    """Progress bar with steps.

    https://stackoverflow.com/questions/63004722/how-to-create-a-labelled-qprogressbar-in-pyside
    """

    evt_steps_changed = Signal(list)
    evt_value_changed = Signal(int)

    # Attributes
    RADIUS = 10
    LINE_WIDTH = 5
    HORIZONTAL_PADDING = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        self._labels = []
        self._value = 0

        self._percentage_width = 0
        self._animation = QVariantAnimation(startValue=0.0, endValue=1.0)
        self._animation.setDuration(500)
        self._animation.valueChanged.connect(self.update)

    def get_labels(self) -> list[str]:
        """Get labels."""
        return self._labels

    def set_labels(self, labels: list[str]) -> None:
        """Set labels."""
        self._labels = labels
        self.evt_steps_changed.emit(self._labels)

    labels = Property(list, fget=get_labels, fset=set_labels, notify=evt_steps_changed)

    def get_value(self) -> int:
        """Get value."""
        return self._value

    def set_value(self, value: int) -> None:
        """Set current value."""
        if 0 <= value < len(self.labels) + 1:
            self._value = value
            self.evt_value_changed.emit(value)
            self.update()
            if self.value < len(self.labels):
                self._animation.start()

    value = Property(int, fget=get_value, fset=set_value, notify=evt_value_changed)

    def sizeHint(self) -> QSize:
        """Return the size hint for the widget."""
        return QSize(320, 120)

    def paintEvent(self, event):
        default_line_color = THEMES.get_qt_color("primary")
        incomplete_color = THEMES.get_qt_color("secondary")
        progress_color = THEMES.get_qt_color("success")
        complete_color = THEMES.get_qt_color("success")
        canvas_color = THEMES.get_qt_color("canvas")
        text_color = THEMES.get_qt_color("text")

        painter = QPainter(self)

        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), canvas_color)

        busy_rect = QRect(0, 0, self.width(), self.LINE_WIDTH)
        busy_rect.adjust(self.HORIZONTAL_PADDING, 0, -self.HORIZONTAL_PADDING, 0)
        busy_rect.moveCenter(self.rect().center())

        painter.fillRect(busy_rect, default_line_color)

        number_of_steps = len(self.labels)
        if number_of_steps == 0:
            return

        step_width = busy_rect.width() / number_of_steps
        x = round(self.HORIZONTAL_PADDING + step_width / 2)
        y = round(busy_rect.center().y())

        r = QRect(0, 0, round(1.5 * self.RADIUS), round(1.5 * self.RADIUS))

        font_text = painter.font()
        fm = QFontMetrics(font_text)

        for i, text in enumerate(self.labels, 1):
            r.moveCenter(QPoint(x, y))

            if i <= self.value:
                w = step_width if i < self.value else self._animation.currentValue() * step_width
                r_busy = QRect(0, 0, round(w), round(self.LINE_WIDTH))
                r_busy.moveCenter(busy_rect.center())

                if i < number_of_steps:
                    r_busy.moveLeft(x)
                    painter.fillRect(r_busy, progress_color)

                pen = QPen(complete_color)
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(complete_color)
                painter.drawEllipse(r)
                painter.setPen(canvas_color)
                painter.setPen(complete_color)

            else:
                is_active = (self.value + 1) == i
                pen = QPen(incomplete_color if is_active else default_line_color)
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(canvas_color)
                painter.drawEllipse(r)
                painter.setPen(progress_color if is_active else text_color)

            rect = fm.boundingRect(text)
            rect.moveCenter(QPoint(int(x), round(y + 2 * self.RADIUS)))
            painter.setFont(font_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            x = int(x + step_width)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QPushButton

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)

    progressbar = QtStepProgressBar()
    progressbar.labels = [
        "Step One",
        "Step Two",
        "Step Three",
        "Step Four",
        "Step Five",
        "Complete",
    ]
    ha.addWidget(progressbar)

    button = QPushButton("Next Step")
    ha.addWidget(button)

    def on_clicked():
        progressbar.value = (progressbar.value + 1) % (len(progressbar.labels) + 1)

    button.clicked.connect(on_clicked)

    frame.show()
    sys.exit(app.exec_())
