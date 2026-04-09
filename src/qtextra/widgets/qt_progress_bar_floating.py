"""Floating progress overlay widget anchored to another Qt widget."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_overlay import QtOverlay, _apply_elevated_card_effect


class _QtFloatingProgressBarBody(QFrame):
    """Internal content widget for the floating progress overlay."""

    def __init__(self, parent: QWidget | None = None, text: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("floatingProgressCard")
        _apply_elevated_card_effect(self)
        self.text_label = hp.make_label(
            self,
            text=text,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self.text_label.setObjectName("floatingProgressText")
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName("floatingProgressBar")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.text_label)
        layout.addWidget(self.progress_bar)


class QtFloatingProgressBar(QtOverlay):
    """Floating text-and-progress overlay anchored to another widget.

    The overlay remains in the host widget's coordinate space, so it moves and
    resizes naturally with the host window, dialog, or child widget.
    """

    Y_OFFSET: int = 12

    def __init__(
        self,
        parent: QWidget | None = None,
        text: str = "",
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        widget: QWidget | None = None,
        minimum: int = 0,
        maximum: int = 100,
        value: int = 0,
        busy: bool = False,
        **kwargs,
    ) -> None:
        if parent is None and widget is not None:
            parent = widget.window()
        super().__init__(parent=parent, alignment=alignment, widget=widget, **kwargs)
        self._busy = False
        self._determinate_minimum = int(minimum)
        self._determinate_maximum = int(maximum)
        self._determinate_value = int(value)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(0)

        self._body = _QtFloatingProgressBarBody(parent=self, text=text)
        layout.addWidget(self._body)

        self.setMinimumWidth(220)
        self.setMaximumWidth(420)
        self._apply_determinate_state()
        self.set_busy(busy)
        self._relayout()

    def attach_to(self, widget: QWidget | None) -> None:
        """Attach the overlay to a target widget."""
        if widget is not None and self.parentWidget() is None:
            self.setParent(widget.window())
        super().attach_to(widget)
        self._sync_completion_visibility()

    def text(self) -> str:
        """Return the current status text."""
        return self._body.text_label.text()

    def set_text(self, text: str) -> None:
        """Update the status text shown above the progress bar."""
        self._body.text_label.setText(text)
        self.updateGeometry()
        self._relayout()

    def set_range(self, minimum: int, maximum: int) -> None:
        """Set the determinate range for the progress bar."""
        self._determinate_minimum = int(minimum)
        self._determinate_maximum = int(maximum)
        if self._determinate_value < self._determinate_minimum:
            self._determinate_value = self._determinate_minimum
        if self._determinate_value > self._determinate_maximum:
            self._determinate_value = self._determinate_maximum
        if not self._busy:
            self._apply_determinate_state()
        self._sync_completion_visibility()

    def set_value(self, value: int) -> None:
        """Set the current determinate progress value."""
        self._determinate_value = int(value)
        if not self._busy:
            self._body.progress_bar.setValue(self._determinate_value)
        self._sync_completion_visibility()

    def value(self) -> int:
        """Return the last determinate progress value."""
        return self._determinate_value

    def set_busy(self, is_busy: bool) -> None:
        """Switch between busy and determinate progress modes."""
        self._busy = bool(is_busy)
        if self._busy:
            self._body.progress_bar.setRange(0, 0)
        else:
            self._apply_determinate_state()
        self._sync_completion_visibility()

    def is_busy(self) -> bool:
        """Return whether the overlay is in indeterminate busy mode."""
        return self._busy

    def reset(self) -> None:
        """Reset determinate progress to the current minimum and exit busy mode."""
        self._determinate_value = self._determinate_minimum
        self.set_busy(False)

    @property
    def progress_bar(self) -> QProgressBar:
        """Expose the underlying progress bar widget."""
        return self._body.progress_bar

    @property
    def text_label(self) -> QLabel:
        """Expose the underlying text label widget."""
        return self._body.text_label

    def _apply_determinate_state(self) -> None:
        self._body.progress_bar.setRange(self._determinate_minimum, self._determinate_maximum)
        self._body.progress_bar.setValue(self._determinate_value)

    def _is_complete(self) -> bool:
        return (
            not self._busy
            and self._determinate_maximum > self._determinate_minimum
            and self._determinate_value >= self._determinate_maximum
        )

    def _sync_completion_visibility(self) -> None:
        if self.widget() is None:
            return
        if self._is_complete():
            self.hide()
            return
        self._sync_to_anchor()
        self._relayout()
