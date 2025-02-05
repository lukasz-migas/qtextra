"""Progress bar with label."""

from __future__ import annotations

from napari.utils.events import Event
from qtpy import QtCore
from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from qtextra.utils.progress import Progress


class QtLabeledProgressBar(QWidget):
    """QProgressBar with QLabels for description and ETA."""

    def __init__(self, parent: QWidget | None = None, progress: Progress | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        self.progress = progress

        self.description_label = QLabel()
        self.qt_progress_bar = QProgressBar()
        self.qt_progress_bar.setTextVisible(True)

        layout = QHBoxLayout()
        layout.addWidget(self.description_label)
        layout.addWidget(self.qt_progress_bar)

        pbar_layout = QVBoxLayout(self)
        pbar_layout.addLayout(layout, stretch=True)
        pbar_layout.setContentsMargins(0, 0, 0, 0)
        pbar_layout.setSpacing(0)

        self.setMinimum = self.qt_progress_bar.setMinimum
        self.setMaximum = self.qt_progress_bar.setMaximum

    def setRange(self, min_value: int, max_value: int) -> None:
        """Set range."""
        self.qt_progress_bar.setRange(min_value, max_value)

    def setValue(self, value: int) -> None:
        """Set value."""
        self.qt_progress_bar.setValue(value)
        QApplication.processEvents()

    def setDescription(self, value: str) -> None:
        """Set description."""
        self.description_label.setText(value)
        QApplication.processEvents()

    def _set_value(self, event: Event) -> None:
        self.setValue(event.value)

    def _get_value(self) -> int:
        return self.qt_progress_bar.value()

    def _set_description(self, event: Event) -> None:
        self.setDescription(event.value)

    def _make_indeterminate(self, event: Event) -> None:
        self.setRange(0, 0)

    def _set_eta(self, event: Event) -> None:
        self.qt_progress_bar.setFormat(event.value)

    def _on_clear(self, event: Event) -> None:
        self.description_label.setText("")


def set_progress_bar(progress: Progress, progress_bar: QtLabeledProgressBar):
    """Make progress bar."""
    progress.gui = True
    progress.leave = False

    # connect progress object events to updating progress bar
    progress.events.value.connect(progress_bar._set_value)
    progress.events.description.connect(progress_bar._set_description)
    progress.events.overflow.connect(progress_bar._make_indeterminate)
    progress.events.eta.connect(progress_bar._set_eta)
    progress.events.close.connect(progress_bar._on_clear)

    # set its range etc. based on progress object
    if progress.total is not None:
        progress_bar.setRange(progress.n, progress.total)
        progress_bar.setValue(progress.n)
    else:
        progress_bar.setRange(0, 0)
        progress.total = 0
    progress_bar.setDescription(progress.desc)


def _test(pbar):
    import time

    prog = Progress(range(50))
    set_progress_bar(prog, pbar)
    for _v in prog:
        time.sleep(0.1)
    prog.close()


if __name__ == "__main__":  # pragma: no cover
    import sys
    from functools import partial

    from qtpy.QtWidgets import QPushButton

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)
    frame.setMinimumSize(400, 400)

    pbar1 = QtLabeledProgressBar()
    ha.addWidget(pbar1)

    pbar2 = QtLabeledProgressBar()
    ha.addWidget(pbar2)

    btn = QPushButton("Press me to start")
    btn.clicked.connect(partial(_test, pbar1))
    btn.clicked.connect(partial(_test, pbar2))
    ha.addWidget(btn)

    frame.show()
    sys.exit(app.exec_())
