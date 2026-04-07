"""Vertical progress report widget with labelled steps."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from qtpy.QtCore import Property, QSize, Qt, Signal
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from qtextra._pydantic_compat import BaseModel, ValidationError


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


class _QtProgressReportItem(QWidget):
    """Single styled row within a progress report."""

    MARKER_TEXT: ClassVar[dict[ProgressStepStatus, str]] = {
        ProgressStepStatus.PENDING: "",
        ProgressStepStatus.COMPLETE: "✓",
        ProgressStepStatus.FAILED: "✕",
        ProgressStepStatus.IN_PROGRESS: "•",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the item UI."""
        super().__init__(parent)
        self.setObjectName("progressReportItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        indicator_widget = QWidget(self)
        indicator_widget.setObjectName("progressReportIndicator")
        indicator_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        indicator_layout = QVBoxLayout(indicator_widget)
        indicator_layout.setContentsMargins(0, 0, 0, 0)
        indicator_layout.setSpacing(0)

        self._top_connector = QFrame(indicator_widget)
        self._top_connector.setObjectName("progressReportConnector")
        self._top_connector.setFrameShape(QFrame.Shape.NoFrame)
        self._top_connector.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._marker = QLabel(indicator_widget)
        self._marker.setObjectName("progressReportMarker")
        self._marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._marker.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._marker.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._bottom_connector = QFrame(indicator_widget)
        self._bottom_connector.setObjectName("progressReportConnector")
        self._bottom_connector.setFrameShape(QFrame.Shape.NoFrame)
        self._bottom_connector.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        indicator_layout.addWidget(self._top_connector, 1)
        indicator_layout.addWidget(self._marker, 0, Qt.AlignmentFlag.AlignHCenter)
        indicator_layout.addWidget(self._bottom_connector, 1)

        text_widget = QWidget(self)
        text_widget.setObjectName("progressReportText")
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 2, 0, 2)
        text_layout.setSpacing(2)

        self._title_label = QLabel(text_widget)
        self._title_label.setObjectName("progressReportTitle")
        self._title_label.setWordWrap(True)
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._subtitle_label = QLabel(text_widget)
        self._subtitle_label.setObjectName("progressReportSubtitle")
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._subtitle_label)

        layout.addWidget(indicator_widget, 0)
        layout.addWidget(text_widget, 1)

    def set_step(
        self,
        step: ProgressReportStep,
        top_status: ProgressStepStatus | None,
        bottom_status: ProgressStepStatus | None,
    ) -> None:
        """Apply step data and connector states to the row."""
        self._marker.setText(self.MARKER_TEXT[step.status])
        self._title_label.setText(step.title)
        self._subtitle_label.setText(step.subtitle)
        self._subtitle_label.setVisible(bool(step.subtitle))

        self._set_status_property(self._marker, step.status)
        self._marker.setProperty("active", str(step.active).lower())

        self._set_status_property(self._title_label, step.status)
        self._title_label.setProperty("active", str(step.active).lower())

        self._set_status_property(self._subtitle_label, step.status)
        self._subtitle_label.setProperty("active", str(step.active).lower())

        self._set_connector_status(self._top_connector, top_status)
        self._set_connector_status(self._bottom_connector, bottom_status)

        self._top_connector.setVisible(top_status is not None)
        self._bottom_connector.setVisible(bottom_status is not None)

        for widget in (
            self,
            self._marker,
            self._title_label,
            self._subtitle_label,
            self._top_connector,
            self._bottom_connector,
        ):
            _refresh_styles(widget)

    @staticmethod
    def _set_status_property(widget: QWidget, status: ProgressStepStatus) -> None:
        widget.setProperty("status", status.value)

    @staticmethod
    def _set_connector_status(widget: QWidget, status: ProgressStepStatus | None) -> None:
        widget.setProperty("status", "hidden" if status is None else status.value)


class QtProgressReport(QWidget):
    """Render a vertical list of progress steps with QSS-styled circle markers."""

    evt_steps_changed = Signal(list)

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
        self._items: list[_QtProgressReportItem] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(10)
        self._layout.addStretch(1)

        if steps:
            self.set_steps(steps)

    def get_steps(self) -> list[ProgressReportStep]:
        """Return the configured progress steps."""
        return list(self._steps)

    def set_steps(self, steps: list[ProgressReportStep | dict]) -> None:
        """Set progress steps from models or dictionaries."""
        self._steps = [self._coerce_step(step) for step in steps]
        self._rebuild_items()
        self.evt_steps_changed.emit(self.get_steps())

    steps = Property(list, fget=get_steps, fset=set_steps, notify=evt_steps_changed)

    def set_step_status(self, index: int, status: ProgressStepStatus | str, active: bool | None = None) -> None:
        """Update a single step status and optionally its active state."""
        step = self._steps[index]
        step.status = ProgressStepStatus(status)
        if active is not None:
            step.active = bool(active)
        self._sync_items()
        self.evt_steps_changed.emit(self.get_steps())

    def set_active_step(self, index: int | None) -> None:
        """Mark one step as active and clear the active state on others."""
        if index is not None and not 0 <= index < len(self._steps):
            raise IndexError(f"Step index out of range: {index}")
        for i, step in enumerate(self._steps):
            step.active = i == index
            if step.active and step.status == ProgressStepStatus.PENDING:
                step.status = ProgressStepStatus.IN_PROGRESS
        self._sync_items()
        self.evt_steps_changed.emit(self.get_steps())

    def current_step_index(self) -> int | None:
        """Return the active step index, if any."""
        for index, step in enumerate(self._steps):
            if step.active:
                return index
        return None

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Return the preferred widget size."""
        return QSize(420, max(160, 96 * max(len(self._steps), 1)))

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        """Return the minimum widget size."""
        return QSize(260, max(120, 72 * max(len(self._steps), 1)))

    @staticmethod
    def _coerce_step(step: ProgressReportStep | dict) -> ProgressReportStep:
        if isinstance(step, ProgressReportStep):
            return step
        if isinstance(step, dict):
            return ProgressReportStep(**step)
        raise TypeError(f"Step must be a ProgressReportStep or dict, received {type(step)!r}")

    def _rebuild_items(self) -> None:
        while self._items:
            item = self._items.pop()
            self._layout.removeWidget(item)
            item.deleteLater()

        for index, _step in enumerate(self._steps):
            item = _QtProgressReportItem(self)
            self._layout.insertWidget(index, item)
            self._items.append(item)

        self._sync_items()
        self.updateGeometry()

    def _sync_items(self) -> None:
        for index, (step, item) in enumerate(zip(self._steps, self._items, strict=False)):
            previous_status = self._steps[index - 1].status if index > 0 else None
            next_status = step.status if index < len(self._steps) - 1 else None
            item.set_step(step, top_status=previous_status, bottom_status=next_status)


__all__ = ["ProgressReportStep", "ProgressStepStatus", "QtProgressReport", "ValidationError"]
