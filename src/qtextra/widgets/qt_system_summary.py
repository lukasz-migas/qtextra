import os
from contextlib import suppress

import numba
import psutil
from numba.cuda import CudaSupportError
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from qtextra.utils.utilities import human_readable_byte_size
from qtextra.widgets.qt_dialog import QtFramelessPopup


class SystemSummaryWidget(QWidget):
    """System information."""

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        # CPU summary
        self.cpu_group_box = QGroupBox("CPU Summary")
        self.cpu_group_box_layout = QVBoxLayout()
        self.cpu_group_box_layout.setSpacing(0)
        self.cpu_group_box_layout.setAlignment(Qt.AlignTop)
        self.cpu_group_box.setLayout(self.cpu_group_box_layout)

        # CPU freq
        with suppress(FileNotFoundError):
            cpu = round(psutil.cpu_freq().current, 2)
        cpu = f"{cpu} Mhz" if cpu else "N/A"
        self.cpu_freq_stats_label = QLabel(f"Current CPU frequency:     \t {cpu}", self)
        self.cpu_group_box_layout.addWidget(self.cpu_freq_stats_label)

        # Number of cores
        self.nb_cores_label = QLabel(f"Number of CPU cores:       \t {os.cpu_count() // 2}", self)
        self.cpu_group_box_layout.addWidget(self.nb_cores_label)
        if (os.cpu_count() // 2) < 4:
            self.nb_cores_label.setStyleSheet("QLabel {color: red;}")
        elif (os.cpu_count() // 2) <= 6:
            self.nb_cores_label.setStyleSheet("QLabel {color: orange;}")
        else:
            self.nb_cores_label.setStyleSheet("QLabel {color: green;}")

        self.cpu_load_values = [(elem * 16) for elem in psutil.getloadavg()]
        cpu_1min = "100.0+" if self.cpu_load_values[0] >= 100.0 else round(self.cpu_load_values[0], 2)
        self.cpu_load_label0 = QLabel(f"CPU load over last 1 min:  \t {cpu_1min}%", self)
        self.cpu_group_box_layout.addWidget(self.cpu_load_label0)

        cpu_5min = "100.0+" if self.cpu_load_values[1] >= 100.0 else round(self.cpu_load_values[1], 2)
        self.cpu_load_label1 = QLabel(f"CPU load over last 5 mins: \t {cpu_5min}%", self)
        self.cpu_group_box_layout.addWidget(self.cpu_load_label1)

        cpu_15min = "100.0+" if self.cpu_load_values[2] >= 100.0 else round(self.cpu_load_values[2], 2)
        self.cpu_load_label2 = QLabel(f"CPU load over last 15 mins:\t {cpu_15min}%", self)
        self.cpu_group_box_layout.addWidget(self.cpu_load_label2)

        if self.cpu_load_values[0] >= 30:
            self.cpu_load_label0.setStyleSheet("QLabel {color: red;}")
        elif self.cpu_load_values[0] > 15:
            self.cpu_load_label0.setStyleSheet("QLabel {color: orange;}")
        else:
            self.cpu_load_label0.setStyleSheet("QLabel {color: green;}")
        if self.cpu_load_values[1] >= 30:
            self.cpu_load_label1.setStyleSheet("QLabel {color: red;}")
        elif self.cpu_load_values[1] > 15:
            self.cpu_load_label1.setStyleSheet("QLabel {color: orange;}")
        else:
            self.cpu_load_label1.setStyleSheet("QLabel {color: green;}")
        if self.cpu_load_values[2] >= 30:
            self.cpu_load_label2.setStyleSheet("QLabel {color: red;}")
        elif self.cpu_load_values[2] > 15:
            self.cpu_load_label2.setStyleSheet("QLabel {color: orange;}")
        else:
            self.cpu_load_label2.setStyleSheet("QLabel {color: green;}")

        # Memory summary
        self.memory_group_box = QGroupBox("Memory Summary")
        self.memory_group_box_layout = QVBoxLayout()
        self.memory_group_box_layout.setSpacing(0)
        self.memory_group_box_layout.setAlignment(Qt.AlignTop)
        self.memory_group_box.setLayout(self.memory_group_box_layout)

        self.free_memory_label = QLabel(
            f"Free Memory:\t {human_readable_byte_size(psutil.virtual_memory().available)}, "
            f"({round(100 * psutil.virtual_memory().available / psutil.virtual_memory().total, 2)}%)",
            self,
        )
        self.memory_group_box_layout.addWidget(self.free_memory_label)
        if psutil.virtual_memory().available < 8000000000:
            self.free_memory_label.setStyleSheet("QLabel {color: red;}")
        elif psutil.virtual_memory().available < 32000000000:
            self.free_memory_label.setStyleSheet("QLabel {color: orange;}")
        else:
            self.free_memory_label.setStyleSheet("QLabel {color: green;}")

        self.total_memory_label = QLabel(
            f"Total Memory:\t {human_readable_byte_size(psutil.virtual_memory().total)}",
            self,
        )
        self.memory_group_box_layout.addWidget(self.total_memory_label)
        if psutil.virtual_memory().total < 8000000000:
            self.total_memory_label.setStyleSheet("QLabel {color: red;}")
        elif psutil.virtual_memory().total < 32000000000:
            self.total_memory_label.setStyleSheet("QLabel {color: orange;}")
        else:
            self.total_memory_label.setStyleSheet("QLabel {color: green;}")

        # GPU summary
        self.gpu_group_box = QGroupBox("GPU Summary")
        self.gpu_group_box_layout = QVBoxLayout()
        self.gpu_group_box_layout.setSpacing(0)
        self.gpu_group_box_layout.setAlignment(Qt.AlignTop)
        self.gpu_group_box.setLayout(self.gpu_group_box_layout)

        try:
            cuda_gpu_name = numba.cuda.get_current_device().name.decode()
        except CudaSupportError:
            cuda_gpu_name = "N/A"

        self.cuda_gpu_label = QLabel(f"CUDA GPU: \t\t{cuda_gpu_name}", self)
        self.gpu_group_box_layout.addWidget(self.cuda_gpu_label)

        if cuda_gpu_name != "N/A":
            self.cuda_gpu_label.setStyleSheet("QLabel {color: green;}")
        else:
            self.cuda_gpu_label.setStyleSheet("QLabel {color: red;}")

        # cuda_toolkit = numba.cuda.cudadrv.nvvm.is_available()
        # self.cudatoolkit_label = QLabel(f"CUDA Toolkit: \t\t{'present' if cuda_toolkit else 'absent'}", self)
        # self.gpu_group_box_layout.addWidget(self.cudatoolkit_label)
        #
        # if numba.cuda.cudadrv.nvvm.is_available():
        #     self.cudatoolkit_label.setStyleSheet("QLabel {color: green;}")
        # else:
        #     self.cudatoolkit_label.setStyleSheet("QLabel {color: red;}")

        try:
            cuda_memory_free = numba.cuda.current_context().get_memory_info().free
            cuda_memory_total = numba.cuda.current_context().get_memory_info().total
        except CudaSupportError:
            cuda_memory_free = 0
            cuda_memory_total = 0

        self.gpu_memory_free_label = QLabel(f"Free GPU Memory: \t{human_readable_byte_size(cuda_memory_free)}", self)
        self.gpu_group_box_layout.addWidget(self.gpu_memory_free_label)

        self.gpu_memory_total_label = QLabel(f"Total GPU Memory: \t{human_readable_byte_size(cuda_memory_total)}", self)
        self.gpu_group_box_layout.addWidget(self.gpu_memory_total_label)

        if cuda_memory_total == 0:
            self.gpu_memory_total_label.setStyleSheet("QLabel {color: red;}")
            self.gpu_memory_free_label.setStyleSheet("QLabel {color: red;}")
        else:
            if numba.cuda.current_context().get_memory_info().total < 8000000000:
                self.gpu_memory_total_label.setStyleSheet("QLabel {color: orange;}")
            else:
                self.gpu_memory_total_label.setStyleSheet("QLabel {color: green;}")

            if cuda_memory_free / cuda_memory_total < 0.4:
                self.gpu_memory_free_label.setStyleSheet("QLabel {color: red;}")
            elif cuda_memory_free / cuda_memory_total < 0.8:
                self.gpu_memory_free_label.setStyleSheet("QLabel {color: orange;}")
            else:
                self.gpu_memory_free_label.setStyleSheet("QLabel {color: green;}")

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.cpu_group_box)
        self.layout.addWidget(self.memory_group_box)
        self.layout.addWidget(self.gpu_group_box)


class SystemSummaryPopup(QtFramelessPopup):
    """Show summary of the system."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def make_panel(self):
        """Create widget."""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(SystemSummaryWidget(self))
        return layout


if __name__ == "__main__":  # pragma: no cover

    def _main():
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qmain

        def _toggle_theme():
            THEMES.theme = choice(THEMES.available_themes())
            THEMES.set_theme_stylesheet(frame)

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)

        wdg = make_btn(frame, "Click here to toggle theme")
        wdg.clicked.connect(_toggle_theme)
        ha.addWidget(wdg)

        wdg = SystemSummaryWidget(parent=frame)
        ha.addWidget(wdg)

        frame.show()
        sys.exit(app.exec_())

    _main()
