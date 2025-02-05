"""Progress bar."""

from qtpy.QtCore import Property, QPoint, QRect, QSize, Qt, QVariantAnimation, Signal
from qtpy.QtGui import QColor, QFontMetrics, QPainter, QPen
from qtpy.QtWidgets import QWidget


class QtStepProgressBar(QWidget):
    """Progress bar with steps.

    https://stackoverflow.com/questions/63004722/how-to-create-a-labelled-qprogressbar-in-pyside
    """

    stepsChanged = Signal(list)
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._labels = []
        self._value = 0

        self._percentage_width = 0
        self._animation = QVariantAnimation(startValue=0.0, endValue=1.0)
        self._animation.setDuration(500)
        self._animation.valueChanged.connect(self.update)

    def get_labels(self):
        return self._labels

    def set_labels(self, labels):
        self._labels = labels[:]
        self.stepsChanged.emit(self._labels)

    labels = Property(list, fget=get_labels, fset=set_labels, notify=stepsChanged)

    def get_value(self):
        return self._value

    def set_value(self, value):
        if 0 <= value < len(self.labels) + 1:
            self._value = value
            self.valueChanged.emit(value)
            self.update()
            if self.value < len(self.labels):
                self._animation.start()

    value = Property(int, fget=get_value, fset=set_value, notify=valueChanged)

    def sizeHint(self):
        return QSize(320, 120)

    def paintEvent(self, event):
        grey = QColor("#777")
        grey2 = QColor("#dfe3e4")
        blue = QColor("#2183dd")
        green = QColor("#009900")
        white = QColor("#fff")

        painter = QPainter(self)

        painter.setRenderHints(QPainter.Antialiasing)

        height = 5
        offset = 10

        painter.fillRect(self.rect(), white)

        busy_rect = QRect(0, 0, self.width(), height)
        busy_rect.adjust(offset, 0, -offset, 0)
        busy_rect.moveCenter(self.rect().center())

        painter.fillRect(busy_rect, grey2)

        number_of_steps = len(self.labels)

        if number_of_steps == 0:
            return

        step_width = busy_rect.width() / number_of_steps
        x = int(round(offset + step_width / 2))
        y = int(round(busy_rect.center().y()))
        radius = 10

        font_text = painter.font()

        # font_icon = QFont("Font Awesome 5 Free")
        # font_icon.setPixelSize(radius)

        r = QRect(0, 0, round(1.5 * radius), round(1.5 * radius))
        fm = QFontMetrics(font_text)

        for i, text in enumerate(self.labels, 1):
            r.moveCenter(QPoint(x, y))

            if i <= self.value:
                w = step_width if i < self.value else self._animation.currentValue() * step_width
                r_busy = QRect(0, 0, round(w), round(height))
                r_busy.moveCenter(busy_rect.center())

                if i < number_of_steps:
                    r_busy.moveLeft(x)
                    painter.fillRect(r_busy, blue)

                pen = QPen(green)
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(green)
                painter.drawEllipse(r)
                # painter.setFont(font_icon)
                painter.setPen(white)
                # painter.drawText(r, Qt.AlignmentFlag.AlignCenter, chr(0xF00C))
                painter.setPen(green)

            else:
                is_active = (self.value + 1) == i
                pen = QPen(grey if is_active else grey2)
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(white)
                painter.drawEllipse(r)
                painter.setPen(blue if is_active else QColor("black"))

            rect = fm.boundingRect(text)
            rect.moveCenter(QPoint(int(x), int(round(y + 2 * radius))))
            painter.setFont(font_text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

            x += step_width


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QPushButton

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)

    progressbar = QtStepProgressBar()
    progressbar.labels = ["Step One", "Step Two", "Step Three", "Complete"]
    ha.addWidget(progressbar)

    button = QPushButton("Next Step")
    ha.addWidget(button)

    def on_clicked():
        progressbar.value = (progressbar.value + 1) % (len(progressbar.labels) + 1)

    button.clicked.connect(on_clicked)

    frame.show()
    sys.exit(app.exec_())
