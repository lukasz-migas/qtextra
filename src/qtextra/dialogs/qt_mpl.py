"""Matplotlib popup."""

from __future__ import annotations

import numpy as np

import qtextra.helpers as hp
from qtextra._visuals.mpl.views import ViewMplLine
from qtpy.QtWidgets import QVBoxLayout, QWidget
from qtextra.widgets.qt_dialog import QtFramelessTool


class QtMplPopup(QtFramelessTool):
    """Very simple popup window to show spectrum."""

    def __init__(
        self,
        parent: QWidget,
        x_label: str = "x-axis",
        y_label: str = "y-axis",
        title: str = "",
    ):
        self._x_label = x_label
        self._y_label = y_label
        super().__init__(parent)
        self.setMaximumSize(600, 400)
        self.set_title(title)

    @property
    def title(self) -> str:
        """Get title of the widget."""
        return self._title_label.text()

    @title.setter
    def title(self, value: str) -> None:
        self._title_label.setText(value)

    @property
    def x_label(self) -> str:
        """Get x-axis label."""
        return self.view.x_label

    @x_label.setter
    def x_label(self, value: str) -> None:
        self.view.x_label = value

    def set_title(self, title: str) -> None:
        """Set title on the layout."""
        self._title_label.setText(title)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Make panel."""
        _, handle_layout = self._make_close_handle()

        self.view = ViewMplLine(self, x_label=self._x_label, y_label=self._y_label, axes_size=[0.1, 0.2, 0.8, 0.8])

        layout = QVBoxLayout()
        layout.addLayout(handle_layout)
        layout.addWidget(hp.make_h_line(self))
        layout.addWidget(self.view.figure, stretch=1)
        return layout

    def plot(self, x: np.ndarray, y: np.ndarray) -> None:
        """Visualise spectrum."""
        self.view.plot(x, y)

    def add_marker(self, x: float, y: float, width: float) -> None:
        """Add patch to the spectrum."""
        self.view.add_vline(x)
        self.view.add_patch(x - (width / 2), y, width)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    _ = qapplication()  # analysis:ignore
    # dlg = SpectrumPlotPopup(None, title="Spectrum viewer")
    dlg = QtMplPopup(None, title="Spectrum viewer")
    apply_style(dlg)
    dlg.plot(np.arange(100), np.arange(100))
    dlg.show()
    sys.exit(dlg.exec_())
