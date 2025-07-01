"""Tutorial widget."""

import typing as ty
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator
from qtpy.QtCore import QEasingCurve, QPoint, Qt, QVariantAnimation
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

import qtextra.helpers as hp


class Position(str, Enum):
    """Position."""

    CENTER = "center"

    LEFT_TOP = "left_top"
    LEFT = "left"
    LEFT_BOTTOM = "left_bottom"

    RIGHT_TOP = "right_top"
    RIGHT = "right"
    RIGHT_BOTTOM = "right_bottom"

    TOP_LEFT = "top_left"
    TOP = "top"
    TOP_RIGHT = "top_right"

    BOTTOM_LEFT = "bottom_left"
    BOTTOM = "bottom"
    BOTTOM_RIGHT = "bottom_right"


class TutorialStep(BaseModel):
    """Tutorial step.

    Attributes
    ----------
    title: str
        Title of the tutorial step.
    message: str
        Message to display. Can be HTML.
    widget: QWidget
        Widget to associate tutorial with. If widget is provided, chevron icon will be shown and it will point towards
        it.
    position: Position
        The position of the tutorial chevron.
    position_offset: tuple[int, int]
        Offset position of the tutorial chevron.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str = ""
    message: str
    widget: QWidget
    position: Position = Position.RIGHT
    position_offset: tuple[int, int] = (0, 0)
    func: ty.Optional[tuple[ty.Callable, ...]] = None

    @field_validator("widget", mode="before")
    def validate_widget(widget: QWidget) -> QWidget:
        """Validate widget."""
        if not isinstance(widget, QWidget):
            raise ValueError(f"Invalid widget '{widget}'.")
        return widget


class QtTutorial(QDialog):
    """Tutorial step widget."""

    # Window attributes
    MIN_WIDTH = 350
    MAX_WIDTH = 450
    MIN_HEIGHT = 40
    ALLOW_CHEVRON = True

    _current = -1
    steps: ty.List[TutorialStep]
    chevrons: ty.Dict[str, ty.Optional[QWidget]]

    def __init__(self, parent: ty.Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setSizeGripEnabled(False)
        self.setModal(False)

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        self._animation = QVariantAnimation()
        self._animation.setDuration(500)
        self._animation.valueChanged.connect(self._update_progress)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # self._move_animation = QVariantAnimation()
        # self._move_animation.setDuration(1000)
        # self._move_animation.valueChanged.connect(self._update_position)
        # self._move_animation.setEasingCurve(QEasingCurve.InOutCubic)

        self.steps = []
        self.make_ui()
        if not self.ALLOW_CHEVRON:
            for chevron in self.chevrons.values():
                chevron.hide()

    # noinspection PyAttributeOutsideInit
    def make_ui(self) -> None:
        """Setup UI."""
        self.chevron_up_left = hp.make_qta_label(self, "chevron_up_circle", small=True, retain_size=False)
        self.chevron_up_mid = hp.make_qta_label(self, "chevron_up_circle", small=True, retain_size=False)
        self.chevron_up_right = hp.make_qta_label(self, "chevron_up_circle", small=True, retain_size=False)

        self.chevron_down_left = hp.make_qta_label(self, "chevron_down_circle", small=True, retain_size=False)
        self.chevron_down_mid = hp.make_qta_label(self, "chevron_down_circle", small=True, retain_size=False)
        self.chevron_down_right = hp.make_qta_label(self, "chevron_down_circle", small=True, retain_size=False)

        self.chevron_left_top = hp.make_qta_label(self, "chevron_left_circle", small=True, retain_size=False)
        self.chevron_left_mid = hp.make_qta_label(self, "chevron_left_circle", small=True, retain_size=False)
        self.chevron_left_bottom = hp.make_qta_label(self, "chevron_left_circle", small=True, retain_size=False)

        self.chevron_right_top = hp.make_qta_label(self, "chevron_right_circle", small=True, retain_size=False)
        self.chevron_right_mid = hp.make_qta_label(self, "chevron_right_circle", small=True, retain_size=False)
        self.chevron_right_bottom = hp.make_qta_label(self, "chevron_right_circle", small=True, retain_size=False)

        self.chevrons = {
            Position.CENTER: None,
            Position.TOP_LEFT: self.chevron_up_left,
            Position.TOP: self.chevron_up_mid,
            Position.TOP_RIGHT: self.chevron_up_right,
            Position.BOTTOM_LEFT: self.chevron_down_left,
            Position.BOTTOM: self.chevron_down_mid,
            Position.BOTTOM_RIGHT: self.chevron_down_right,
            Position.LEFT_TOP: self.chevron_left_top,
            Position.LEFT: self.chevron_left_mid,
            Position.LEFT_BOTTOM: self.chevron_left_bottom,
            Position.RIGHT_TOP: self.chevron_right_top,
            Position.RIGHT: self.chevron_right_mid,
            Position.RIGHT_BOTTOM: self.chevron_right_bottom,
        }

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
        self._message_label = hp.make_label(self, "", wrap=True, selectable=True, enable_url=True)

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
        main_layout.setRowStretch(3, True)
        # top
        main_layout.addWidget(self.chevron_up_left, 0, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addWidget(self.chevron_up_mid, 0, 1, 1, -1, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addWidget(self.chevron_up_right, 0, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        # content
        main_layout.addLayout(layout, 1, 1, 3, 1)
        # left
        main_layout.addWidget(self.chevron_left_top, 2, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(self.chevron_left_mid, 3, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(self.chevron_left_bottom, 4, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        # right
        main_layout.addWidget(self.chevron_right_top, 2, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(self.chevron_right_mid, 3, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(self.chevron_right_bottom, 4, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        # bottom
        main_layout.addWidget(self.chevron_down_left, 5, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addWidget(self.chevron_down_mid, 5, 1, 1, -1, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addWidget(self.chevron_down_right, 5, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _update_progress(self, value: int) -> None:
        """Update progress bar."""
        self._step_indicator.setValue(value)

    def set_steps(self, steps: ty.List[TutorialStep]) -> None:
        """Set steps."""
        self.steps = steps
        self._step_indicator.setMinimum(0)
        self._step_indicator.setMaximum(len(steps) * 100)
        self.set_step(0)

    def add_step(self, step: TutorialStep) -> None:
        """Add a step to the tutorial."""
        self.steps.append(step)
        self._step_indicator.setMinimum(0)
        self._step_indicator.setMaximum(len(self.steps) * 100)
        self.set_step(0)

    def set_step(self, index: int) -> None:
        """Show step."""
        self._current = index

        step = self.steps[index]
        if step.func:
            for func in step.func:
                func()
        self._title_label.setText(step.title)
        self._message_label.setText(step.message)
        self._step_label.setText(f"Step {index + 1}/{len(self.steps)}")

        # enable/disable buttons
        hp.disable_widgets(self._prev_btn, disabled=index == 0)
        self._next_btn.setText("Next" if index < len(self.steps) - 1 else "Done")
        # move tutorial to specified location
        self._message_label.adjustSize()
        self.adjustSize()
        self.set_chevron(step.position)
        self.move_to_widget(step.widget, step.position, step.position_offset)

        # update animation
        self._animation.setStartValue(self._step_indicator.value())
        self._animation.setEndValue((index + 1) * 100)
        self._animation.start()

    def move_to_widget(
        self, widget: QWidget, position: str = "right", position_offset: tuple[int, int] = (0, 0)
    ) -> None:
        """Move tutorial to specified widget."""
        position = Position(position)
        x_pad, y_pad = 5, 5
        popup_size = self.size()
        chevron = self.chevrons[position]
        if chevron:
            icon_pos = chevron.pos()
            x_offset = int(chevron.size().width() / 2)
            y_offset = int(chevron.size().height() / 2)
        else:
            icon_pos = QPoint(0, 0)
            x_offset = 0
            y_offset = 0

        x_pos_offset, y_pos_offset = position_offset
        rect_of_widget = widget.rect()
        if position in ["right", "right_top", "right_bottom"]:
            x = rect_of_widget.left() - popup_size.width() - x_pad - x_pos_offset
            y = rect_of_widget.center().y() - icon_pos.y() - y_offset - y_pos_offset
        elif position in ["left", "left_top", "left_bottom"]:
            x = rect_of_widget.right() + x_pad - x_pos_offset
            y = rect_of_widget.center().y() - icon_pos.y() - y_offset - y_pos_offset
        elif position in ["bottom", "bottom_left", "bottom_right"]:
            x = rect_of_widget.center().x() - icon_pos.x() - x_offset - x_pos_offset
            y = rect_of_widget.top() - popup_size.height() - y_pad - y_pos_offset
        elif position in ["top", "top_left", "top_right"]:
            x = rect_of_widget.center().x() - icon_pos.x() - x_offset - x_pos_offset
            y = rect_of_widget.bottom() + y_pad - y_pos_offset
        elif position in ["center"]:
            x = rect_of_widget.center().x() - popup_size.width() / 2
            y = rect_of_widget.center().y() - popup_size.height() / 2
        else:
            raise ValueError(f"Invalid position '{position}'.")
        pos = widget.mapToGlobal(QPoint(int(x), int(y)))
        pos = hp.check_if_outside_for_mouse(pos, popup_size)
        self.move(pos)

    def set_chevron(self, position: Position) -> None:
        """Show/hide chevron icons as required."""
        position = Position(position)
        if self.ALLOW_CHEVRON:
            for key, chevron in self.chevrons.items():
                if not chevron:
                    continue
                chevron.setVisible(key == position)

    def on_next(self) -> None:
        """Next step."""
        if self._current == len(self.steps) - 1:
            self.close()
        else:
            self.set_step(self._current + 1)

    def on_prev(self) -> None:
        """Previous step."""
        if self._current > 0:
            self.set_step(self._current - 1)

    def show(self) -> None:
        """Show widget."""
        if self._current == -1:
            self.on_next()
        super().show()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Key press event handler."""
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.on_prev()
            event.accept()
        elif key == Qt.Key.Key_Right:
            self.on_next()
            event.accept()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    def _popover(frame, widget):
        text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore
        et dolore magna aliqua. Vestibulum lorem sed risus ultricies tristique nulla aliquet. Malesuada nunc vel risus
         commodo viverra maecenas. Nascetur ridiculus mus mauris vitae ultricies leo. Tellus in hac habitasse platea
         dictumst vestibulum rhoncus. Egestas fringilla phasellus faucibus scelerisque eleifend donec pretium vulputate.
         Amet nulla facilisi morbi tempus iaculis urna id volutpat lacus. Aliquet nec ullamcorper sit amet risus nullam
         eget felis. Pharetra magna ac placerat vestibulum lectus. Dignissim convallis aenean et tortor at risus. Vitae
         tempus quam pellentesque nec nam aliquam sem et. Pulvinar proin gravida hendrerit lectus."""
        pop = QtTutorial(frame)
        pop.set_steps(
            [
                TutorialStep(
                    title=f"{position}",
                    message=text,
                    widget=widget,
                    position=position,
                )
                for position in Position
            ]
        )
        pop.show()

    app, frame, ha = qframe()

    _popover(frame, frame)
    frame.show()
    frame.setMaximumHeight(400)

    sys.exit(app.exec_())
