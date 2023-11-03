"""Tutorial widget."""
import typing as ty

from pydantic import BaseModel
from qtpy.QtCore import QEasingCurve, QPoint, Qt, QVariantAnimation
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

import qtextra.helpers as hp


class TutorialStep(BaseModel):
    """Tutorial step."""

    title: str = ""
    message: str
    widget: QWidget
    position: str = "right"

    class Config:
        """Configuration."""

        arbitrary_types_allowed = True


class QtTutorial(QDialog):
    """Tutorial step widget."""

    # Window attributes
    MIN_WIDTH = 350
    MAX_WIDTH = 450
    MIN_HEIGHT = 40
    ALLOW_CHEVRON = True

    _current = -1
    _steps = None

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setSizeGripEnabled(False)
        self.setModal(False)

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        self._animation = QVariantAnimation()
        self._animation.setDuration(500)
        self._animation.valueChanged.connect(self._update_progress)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

        # self._move_animation = QVariantAnimation()
        # self._move_animation.setDuration(1000)
        # self._move_animation.valueChanged.connect(self._update_position)
        # self._move_animation.setEasingCurve(QEasingCurve.InOutCubic)

        self.make_ui()
        if not self.ALLOW_CHEVRON:
            self.chevron_up_mid.hide()
            self.chevron_down_mid.hide()
            self.chevron_left_mid.hide()
            self.chevron_right_mid.hide()

    # noinspection PyAttributeOutsideInit
    def make_ui(self):
        """Setup UI."""
        self.chevron_up_mid = hp.make_qta_label(self, "chevron_up_circle", small=True)
        # self.chevron_up_left = hp.make_qta_label(self, "chevron_up_circle", small=True)
        # self.chevron_up_right = hp.make_qta_label(self, "chevron_up_circle", small=True)
        self.chevron_down_mid = hp.make_qta_label(self, "chevron_down_circle", small=True)
        self.chevron_left_mid = hp.make_qta_label(self, "chevron_left_circle", small=True)
        self.chevron_right_mid = hp.make_qta_label(self, "chevron_right_circle", small=True)

        header_widget = QWidget(self)
        header_widget.setObjectName("tutorial_header")

        self._step_indicator = QProgressBar(header_widget)
        self._step_indicator.setObjectName("step_indicator")
        self._step_indicator.setTextVisible(False)
        self._close_btn = hp.make_qta_btn(
            header_widget, "cross", small=True, medium=False, func=self.close, tooltip="Close popup."
        )

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(2, 2, 2, 2)
        header_layout.addWidget(self._step_indicator, stretch=True)
        header_layout.addWidget(self._close_btn)

        self._title_label = hp.make_label(self, "", bold=True)
        self._message_label = hp.make_label(self, "", wrap=True, selectable=True)

        footer_widget = QWidget(self)
        footer_widget.setObjectName("tutorial_footer")
        self._step_label = hp.make_label(footer_widget, "", object_name="step_label")
        self._prev_btn = hp.make_btn(footer_widget, "Previous", func=self.on_prev, tooltip="Show previous step.")
        self._next_btn = hp.make_btn(footer_widget, "Next", func=self.on_next, tooltip="Show next step.")

        footer_layout = QHBoxLayout(footer_widget)
        footer_widget.setContentsMargins(2, 2, 2, 2)
        footer_layout.addWidget(self._step_label, stretch=True)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self._prev_btn)
        footer_layout.addWidget(self._next_btn)

        # layout
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        layout.addWidget(header_widget)
        layout.addWidget(self._title_label)
        layout.addWidget(self._message_label, stretch=True)
        layout.addWidget(footer_widget)

        main_layout = QGridLayout(self)
        # widget, row, column, rowspan, colspan
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)
        main_layout.setColumnStretch(1, True)
        main_layout.setRowStretch(1, True)
        main_layout.addWidget(self.chevron_up_mid, 0, 1, 1, -1, alignment=Qt.AlignHCenter)
        main_layout.addLayout(layout, 1, 1, 1, 1)
        main_layout.addWidget(self.chevron_left_mid, 1, 0, 1, 1, alignment=Qt.AlignVCenter)
        main_layout.addWidget(self.chevron_right_mid, 1, 2, 1, 1, alignment=Qt.AlignVCenter)
        main_layout.addWidget(self.chevron_down_mid, 2, 1, 1, -1, alignment=Qt.AlignHCenter)

    def _update_progress(self, value: float):
        """Update progress bar."""
        self._step_indicator.setValue(value)

    def set_steps(self, steps: ty.List[TutorialStep]):
        """Set steps."""
        self._steps = steps
        self._step_indicator.setMinimum(0)
        self._step_indicator.setMaximum(len(steps) * 100)
        self.set_step(0)

    def set_step(self, index: int):
        """Show step."""
        self._current = index

        step = self._steps[index]
        self._title_label.setText(step.title)
        self._message_label.setText(step.message)
        self._step_label.setText(f"Step {index + 1}/{len(self._steps)}")

        # enable/disable buttons
        hp.disable_widgets(self._prev_btn, disabled=index == 0)
        self._next_btn.setText("Next" if index < len(self._steps) - 1 else "Done")
        # move tutorial to specified location
        self._message_label.adjustSize()
        self.adjustSize()
        self.set_chevron(step.position)
        self.move_to_widget(step.widget, step.position)

        # update animation
        self._animation.setStartValue(self._step_indicator.value())
        self._animation.setEndValue((index + 1) * 100)
        self._animation.start()

    def move_to_widget(self, widget: QWidget, position: str = "right"):
        """Move tutorial to specified widget."""
        x_pad, y_pad = 5, 5
        size = self.size()
        rect = widget.rect()
        if position == "left":
            x = rect.left() - size.width() - x_pad
            y = rect.center().y() - (size.height() * 0.5)
        elif position == "right":
            x = rect.right() + x_pad
            y = rect.center().y() - (size.height() * 0.5)
        elif position == "top":
            x = rect.center().x() - (size.width() * 0.5)
            y = rect.top() - size.height() - y_pad
        elif position == "bottom":
            x = rect.center().x() - (size.width() * 0.5)
            y = rect.bottom() + y_pad
        else:
            raise ValueError(f"Invalid position '{position}'.")
        pos = widget.mapToGlobal(QPoint(x, y))
        self.move(pos)

    def set_chevron(self, position: str):
        """Show/hide chevron icons as required."""
        if self.ALLOW_CHEVRON:
            self.chevron_up_mid.setVisible(position == "bottom")
            self.chevron_down_mid.setVisible(position == "top")
            self.chevron_left_mid.setVisible(position == "right")
            self.chevron_right_mid.setVisible(position == "left")

    def on_next(self):
        """Next step."""
        if self._current == len(self._steps) - 1:
            self.close()
        else:
            self.set_step(self._current + 1)

    def on_prev(self):
        """Previous step."""
        if self._current > 0:
            self.set_step(self._current - 1)

    def show(self):
        """Show widget."""
        if self._current == -1:
            self.on_next()
        super().show()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Key press event handler."""
        key = event.key()
        if key == Qt.Key_Left:
            self.on_prev()
            event.accept()
        elif key == Qt.Key_Right:
            self.on_next()
            event.accept()
        else:
            super().keyPressEvent(event)


#
def _popover(frame, widget):
    text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vestibulum lorem sed risus ultricies tristique nulla aliquet. Malesuada nunc vel risus commodo viverra maecenas. Nascetur ridiculus mus mauris vitae ultricies leo. Tellus in hac habitasse platea dictumst vestibulum rhoncus. Egestas fringilla phasellus faucibus scelerisque eleifend donec pretium vulputate. Amet nulla facilisi morbi tempus iaculis urna id volutpat lacus. Aliquet nec ullamcorper sit amet risus nullam eget felis. Pharetra magna ac placerat vestibulum lectus. Dignissim convallis aenean et tortor at risus. Vitae tempus quam pellentesque nec nam aliquam sem et. Pulvinar proin gravida hendrerit lectus."""
    pop = QtTutorial(frame)
    pop.set_steps(
        [
            TutorialStep(
                title="Title will be bold",
                message=text,
                widget=widget,
                position="right",
            ),
            TutorialStep(
                title="Title will be bold",
                message=text,
                widget=widget,
                position="left",
            ),
            TutorialStep(
                title="Title will be bold",
                message=text,
                widget=widget,
                position="top",
            ),
            TutorialStep(
                title="Title will be bold",
                message=text,
                widget=widget,
                position="bottom",
            ),
        ]
    )
    pop.show()
