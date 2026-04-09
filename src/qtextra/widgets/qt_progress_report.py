"""Vertical progress report widget with labelled steps."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from qtpy.QtCore import Property, QEasingCurve, QRect, QSize, Qt, QTimer, QVariantAnimation, Signal
from qtpy.QtGui import QColor, QPainter, QPainterPath, QPen
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from qtextra._pydantic_compat import BaseModel, ValidationError
from qtextra.config import THEMES

__all__ = ["ProgressReportStep", "ProgressStepStatus", "QtProgressReport", "ValidationError"]


class ProgressStepStatus(str, Enum):
    """Available states for a progress report step."""

    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


class ProgressReportStep(BaseModel):
    """Declarative data model for a single progress report step."""

    title: str
    subtitle: str = ""
    status: ProgressStepStatus = ProgressStepStatus.PENDING
    active: bool = False


def _refresh_styles(widget: QWidget) -> None:
    """Re-polish a widget after dynamic property changes."""
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class _QtProgressReportText(QWidget):
    """Styled title and subtitle labels for one progress-report step."""

    TITLE_SUBTITLE_SPACING: ClassVar[int] = 4

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the label container."""
        super().__init__(parent)
        self.setObjectName("progressReportText")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.TITLE_SUBTITLE_SPACING)

        self.title_label = QLabel(self)
        self.title_label.setObjectName("progressReportTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setIndent(0)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.subtitle_label = QLabel(self)
        self.subtitle_label.setObjectName("progressReportSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setIndent(0)
        self.subtitle_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

    def set_step(self, step: ProgressReportStep) -> None:
        """Apply step content and styling properties to the labels."""
        self.title_label.setText(step.title)
        self.title_label.setProperty("status", step.status.value)
        self.title_label.setProperty("active", step.active)

        self.subtitle_label.setText(step.subtitle)
        self.subtitle_label.setVisible(bool(step.subtitle))
        self.subtitle_label.setProperty("status", step.status.value)
        self.subtitle_label.setProperty("active", step.active)

        _refresh_styles(self.title_label)
        _refresh_styles(self.subtitle_label)

    def content_height_for_width(self, width: int) -> int:
        """Return the wrapped label height for a given width."""
        title_height = self.title_label.heightForWidth(width)
        subtitle_height = self.subtitle_label.heightForWidth(width) if self.subtitle_label.isVisible() else 0
        return title_height + (self.TITLE_SUBTITLE_SPACING + subtitle_height if subtitle_height else 0)


class QtProgressReport(QWidget):
    """Render a vertical list of progress steps with painted markers and QSS-styled text."""

    evt_steps_changed = Signal(list)

    LEFT_PADDING: ClassVar[int] = 20
    RIGHT_PADDING: ClassVar[int] = 20
    TOP_PADDING: ClassVar[int] = 20
    BOTTOM_PADDING: ClassVar[int] = 20
    CIRCLE_DIAMETER: ClassVar[int] = 24
    LINE_WIDTH: ClassVar[int] = 3
    CONNECTOR_WIDTH: ClassVar[int] = 2
    TEXT_GAP: ClassVar[int] = 18
    ITEM_SPACING: ClassVar[int] = 18
    TITLE_SUBTITLE_SPACING: ClassVar[int] = 4

    def __init__(
        self,
        steps: list[ProgressReportStep | dict] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the progress report widget."""
        super().__init__(parent)
        self.setObjectName("progressReport")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._steps: list[ProgressReportStep] = []
        self._text_widgets: list[_QtProgressReportText] = []
        self._marker_animations: list[QVariantAnimation] = []
        self._marker_animation_values: list[float] = []

        if steps:
            self.set_steps(steps)

    def get_steps(self) -> list[ProgressReportStep]:
        """Return the configured progress steps."""
        return list(self._steps)

    def set_steps(self, steps: list[ProgressReportStep | dict]) -> None:
        """Set progress steps from models or dictionaries."""
        old_statuses = [step.status for step in self._steps]
        self._steps = [self._coerce_step(step) for step in steps]
        self._sync_text_widgets()
        self._start_status_change_animations(old_statuses)
        self.evt_steps_changed.emit(self.get_steps())
        self.updateGeometry()
        self.update()

    steps = Property(list, fget=get_steps, fset=set_steps, notify=evt_steps_changed)

    def set_step_status(self, index: int, status: ProgressStepStatus | str, active: bool | None = None) -> None:
        """Update a single step status and optionally its active state."""
        step = self._steps[index]
        previous_status = step.status
        step.status = ProgressStepStatus(status)
        if active is not None:
            step.active = bool(active)
        self._sync_text_widgets()
        if previous_status != step.status:
            self._marker_animations[index].start()
        self.evt_steps_changed.emit(self.get_steps())
        self.update()

    def set_active_step(self, index: int | None) -> None:
        """Mark one step as active and clear the active state on others."""
        if index is not None and not 0 <= index < len(self._steps):
            raise IndexError(f"Step index out of range: {index}")
        for i, step in enumerate(self._steps):
            previous_status = step.status
            step.active = i == index
            if step.active and step.status == ProgressStepStatus.PENDING:
                step.status = ProgressStepStatus.IN_PROGRESS
            if previous_status != step.status:
                self._marker_animations[i].start()
        self._sync_text_widgets()
        self.evt_steps_changed.emit(self.get_steps())
        self.update()

    def current_step_index(self) -> int | None:
        """Return the active step index, if any."""
        for index, step in enumerate(self._steps):
            if step.active:
                return index
        return None

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Return a size hint that fits the current steps."""
        if not self._steps:
            return QSize(320, 120)

        max_text_width = 0
        total_height = self.TOP_PADDING + self.BOTTOM_PADDING
        for text_widget, _step in zip(self._text_widgets, self._steps, strict=False):
            step_width = max(text_widget.title_label.sizeHint().width(), text_widget.subtitle_label.sizeHint().width())
            max_text_width = max(max_text_width, step_width)
            total_height += max(self.CIRCLE_DIAMETER, text_widget.sizeHint().height())
        total_height += self.ITEM_SPACING * (len(self._steps) - 1)

        return QSize(
            max(320, self.LEFT_PADDING + self.CIRCLE_DIAMETER + self.TEXT_GAP + max_text_width + self.RIGHT_PADDING),
            max(120, total_height),
        )

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        """Return the minimum sensible size for the widget."""
        hint = self.sizeHint()
        return QSize(min(hint.width(), 260), min(hint.height(), 120))

    def resizeEvent(self, event) -> None:
        """Reposition step labels when the widget is resized."""
        super().resizeEvent(event)
        self._layout_text_widgets()

    def showEvent(self, event) -> None:
        """Refresh layout after the widget receives its first final geometry."""
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh_layout_after_show)

    def paintEvent(self, event) -> None:
        """Paint the progress timeline and markers."""
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), THEMES.get_qt_color("canvas"))

        if not self._steps:
            return

        layouts = self._compute_layouts()
        center_x = self.LEFT_PADDING + self.CIRCLE_DIAMETER / 2

        for index, (_, circle_rect, _) in enumerate(layouts[:-1]):
            next_circle_rect = layouts[index + 1][1]
            self._draw_connector(
                painter=painter,
                center_x=center_x,
                top=int(circle_rect.bottom()),
                bottom=int(next_circle_rect.top()),
                step=self._steps[index],
            )

        for index, (step, circle_rect, _text_rect) in enumerate(layouts):
            self._draw_circle(painter, circle_rect, step, index)

    @staticmethod
    def _coerce_step(step: ProgressReportStep | dict) -> ProgressReportStep:
        if isinstance(step, ProgressReportStep):
            return step
        if isinstance(step, dict):
            return ProgressReportStep(**step)
        raise TypeError(f"Step must be a ProgressReportStep or dict, received {type(step)!r}")

    def _sync_text_widgets(self) -> None:
        while len(self._text_widgets) > len(self._steps):
            widget = self._text_widgets.pop()
            widget.deleteLater()
            animation = self._marker_animations.pop()
            animation.stop()
            self._marker_animation_values.pop()

        while len(self._text_widgets) < len(self._steps):
            self._text_widgets.append(_QtProgressReportText(self))
            animation = QVariantAnimation(self)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setDuration(240)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.valueChanged.connect(self._on_marker_animation_value_changed)
            self._marker_animations.append(animation)
            self._marker_animation_values.append(0.0)

        for widget, step in zip(self._text_widgets, self._steps, strict=False):
            widget.set_step(step)
            widget.show()

        self._layout_text_widgets()

    def _layout_text_widgets(self) -> None:
        if not self._steps:
            return

        for text_widget, (_, _, text_rect) in zip(self._text_widgets, self._compute_layouts(), strict=False):
            text_widget.setGeometry(text_rect)

    def _compute_layouts(self) -> list[tuple[ProgressReportStep, QRect, QRect]]:
        available_text_width = max(
            self.width() - self.LEFT_PADDING - self.CIRCLE_DIAMETER - self.TEXT_GAP - self.RIGHT_PADDING,
            120,
        )
        circle_x = self.LEFT_PADDING
        text_x = self.LEFT_PADDING + self.CIRCLE_DIAMETER + self.TEXT_GAP
        y = self.TOP_PADDING
        layouts: list[tuple[ProgressReportStep, QRect, QRect]] = []

        for step, text_widget in zip(self._steps, self._text_widgets, strict=False):
            text_height = text_widget.content_height_for_width(available_text_width)
            item_height = max(self.CIRCLE_DIAMETER, text_height)

            circle_top = y + (item_height - self.CIRCLE_DIAMETER) // 2
            text_top = y + max((item_height - text_height) // 2, 0)

            circle_rect = QRect(circle_x, circle_top, self.CIRCLE_DIAMETER, self.CIRCLE_DIAMETER)
            text_rect = QRect(text_x, text_top, available_text_width, text_height)
            layouts.append((step, circle_rect, text_rect))
            y += item_height + self.ITEM_SPACING

        return layouts

    def _draw_connector(
        self,
        painter: QPainter,
        center_x: float,
        top: int,
        bottom: int,
        step: ProgressReportStep,
    ) -> None:
        pen = QPen(self._connector_color(step))
        pen.setWidth(self.CONNECTOR_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(center_x), top, int(center_x), bottom)

    def _draw_circle(self, painter: QPainter, rect: QRect, step: ProgressReportStep, index: int) -> None:
        border_color, fill_color = self._circle_colors(step)
        animation_value = self._marker_animation_values[index] if index < len(self._marker_animation_values) else 0.0
        if animation_value > 0:
            self._draw_marker_halo(painter, rect, border_color, animation_value)
        pen = QPen(border_color)
        pen.setWidth(self.LINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(fill_color)
        painter.drawEllipse(rect)

        if step.status == ProgressStepStatus.COMPLETE:
            self._draw_check_mark(painter, rect)
        elif step.status == ProgressStepStatus.FAILED:
            self._draw_cross_mark(painter, rect)
        elif step.status == ProgressStepStatus.IN_PROGRESS:
            self._draw_progress_dot(painter, rect, border_color)

    @staticmethod
    def _circle_colors(step: ProgressReportStep) -> tuple[QColor, QColor]:
        canvas = THEMES.get_qt_color("canvas")
        if step.status == ProgressStepStatus.COMPLETE:
            color = THEMES.get_qt_color("success")
            return color, color
        if step.status == ProgressStepStatus.FAILED:
            color = THEMES.get_qt_color("error")
            return color, color
        if step.status == ProgressStepStatus.IN_PROGRESS:
            color = THEMES.get_qt_color("secondary")
            return color, canvas
        color = THEMES.get_qt_color("text")
        return color, canvas

    @staticmethod
    def _connector_color(step: ProgressReportStep) -> QColor:
        if step.status == ProgressStepStatus.COMPLETE:
            return THEMES.get_qt_color("success")
        if step.status == ProgressStepStatus.FAILED:
            return THEMES.get_qt_color("error")
        return THEMES.get_qt_color("text")

    @staticmethod
    def _draw_check_mark(painter: QPainter, rect: QRect) -> None:
        pen = QPen(THEMES.get_qt_color("canvas"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        path = QPainterPath()
        path.moveTo(rect.left() + rect.width() * 0.26, rect.top() + rect.height() * 0.54)
        path.lineTo(rect.left() + rect.width() * 0.44, rect.top() + rect.height() * 0.72)
        path.lineTo(rect.left() + rect.width() * 0.74, rect.top() + rect.height() * 0.32)
        painter.drawPath(path)

    @staticmethod
    def _draw_cross_mark(painter: QPainter, rect: QRect) -> None:
        pen = QPen(THEMES.get_qt_color("canvas"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        inset_lo = rect.width() * 0.3
        inset_hi = rect.width() * 0.7
        painter.drawLine(
            int(rect.left() + inset_lo),
            int(rect.top() + inset_lo),
            int(rect.left() + inset_hi),
            int(rect.top() + inset_hi),
        )
        painter.drawLine(
            int(rect.left() + inset_lo),
            int(rect.top() + inset_hi),
            int(rect.left() + inset_hi),
            int(rect.top() + inset_lo),
        )

    @staticmethod
    def _draw_progress_dot(painter: QPainter, rect: QRect, color: QColor) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        diameter = rect.width() // 3
        dot_rect = QRect(0, 0, diameter, diameter)
        dot_rect.moveCenter(rect.center())
        painter.drawEllipse(dot_rect)
        painter.restore()

    @staticmethod
    def _draw_marker_halo(painter: QPainter, rect: QRect, color: QColor, animation_value: float) -> None:
        painter.save()
        halo_color = QColor(color)
        halo_color.setAlpha(max(0, int(120 * (1.0 - animation_value))))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo_color)
        expansion = int(8 * animation_value)
        painter.drawEllipse(rect.adjusted(-expansion, -expansion, expansion, expansion))
        painter.restore()

    def _start_status_change_animations(self, old_statuses: list[ProgressStepStatus]) -> None:
        for index, step in enumerate(self._steps):
            if index >= len(old_statuses) or old_statuses[index] != step.status:
                self._marker_animations[index].start()

    def _refresh_layout_after_show(self) -> None:
        """Relayout text after style polish and final show-time sizing."""
        self._layout_text_widgets()
        self.updateGeometry()
        self.update()

    def _on_marker_animation_value_changed(self, value: object) -> None:
        animation = self.sender()
        if not isinstance(animation, QVariantAnimation):
            return
        try:
            index = self._marker_animations.index(animation)
        except ValueError:
            return
        self._marker_animation_values[index] = float(value)
        self.update()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)
    frame.setMinimumSize(400, 400)

    pbar1 = QtProgressReport(
        steps=[
            ProgressReportStep(
                title="Current", subtitle="Current task", status=ProgressStepStatus.COMPLETE, active=False
            ),
            ProgressReportStep(title="Failed", subtitle="Failed task", status=ProgressStepStatus.FAILED, active=False),
            ProgressReportStep(title="Next", subtitle="Next task", status=ProgressStepStatus.IN_PROGRESS, active=True),
        ]
    )
    ha.addWidget(pbar1)

    frame.show()
    sys.exit(app.exec_())
