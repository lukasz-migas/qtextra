"""Progress bar with label."""
import typing as ty

from qtpy import QtCore
from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from qtextra.models.progress import Progress


class QtLabeledProgressBar(QWidget):
    """QProgressBar with QLabels for description and ETA."""

    def __init__(self, parent: ty.Optional[QWidget] = None, progress: ty.Optional[Progress] = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.progress = progress

        self.description_label = QLabel()
        self.qt_progress_bar = QProgressBar()
        self.eta_label = QLabel()
        self.eta_label.setObjectName("small")

        layout = QHBoxLayout()
        layout.addWidget(self.description_label)
        layout.addWidget(self.qt_progress_bar)

        pbar_layout = QVBoxLayout(self)
        pbar_layout.addLayout(layout, stretch=True)
        pbar_layout.addWidget(self.eta_label, stretch=True)
        pbar_layout.setContentsMargins(0, 0, 0, 0)
        pbar_layout.setSpacing(0)

        self.setMinimum = self.qt_progress_bar.setMinimum
        self.setMaximum = self.qt_progress_bar.setMaximum

    def setRange(self, min_value: int, max_value: int):
        """Set range."""
        self.qt_progress_bar.setRange(min_value, max_value)

    def setValue(self, value):
        """Set value."""
        self.qt_progress_bar.setValue(value)
        QApplication.processEvents()

    def setDescription(self, value):
        """Set description."""
        self.description_label.setText(value)
        QApplication.processEvents()

    def _set_value(self, event):
        self.setValue(event.value)

    def _get_value(self):
        return self.qt_progress_bar.value()

    def _set_description(self, event):
        self.setDescription(event.value)

    def _make_indeterminate(self, event):
        self.setRange(0, 0)

    def _set_eta(self, event):
        self.eta_label.setText(event.value)

    def _on_clear(self, event):
        self.eta_label.setText("")
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

    prog = Progress(range(100))
    set_progress_bar(prog, pbar)
    for _v in prog:
        time.sleep(0.5)
        # prog.update(1)
    prog.close()


if __name__ == "__main__":  # pragma: no cover
    import sys
    from functools import partial

    from qtpy.QtWidgets import QPushButton

    from qtextra._dev_tools import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)
    frame.setMinimumSize(400, 400)

    pbar = QtLabeledProgressBar()
    ha.addWidget(pbar)

    pbar = QtLabeledProgressBar()
    ha.addWidget(pbar)

    btn = QPushButton("Press me to start")
    btn.clicked.connect(partial(_test, pbar))
    ha.addWidget(btn)

    frame.show()
    sys.exit(app.exec_())
