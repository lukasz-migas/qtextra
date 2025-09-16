"""System summary widget."""

from __future__ import annotations

import os
from contextlib import suppress

import numba
import psutil
from koyo.utilities import human_readable_byte_size
from numba.cuda import CudaSupportError
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup

MEM_USAGE_ERROR = 4e9  # 4 Gb
MEM_USAGE_WARNING = 16e9  # 16 Gb
MEM_ERROR = 8e9
MEM_WARNING = 32e9

CPU_N_ERROR = 30
CPU_N_WARNING = 15

CPU_PERCENT_ERROR = 50
CPU_PERCENT_WARNING = 30


def style_if(widget, value: int, error_if: int, warn_if: int, less: bool = True) -> None:
    """Style widget based on value."""
    if less:
        if value < error_if:
            object_name = "error_status_label"
        elif value < warn_if:
            object_name = "warning_status_label"
        else:
            object_name = "success_status_label"
    else:
        if value > error_if:
            object_name = "error_status_label"
        elif value > warn_if:
            object_name = "warning_status_label"
        else:
            object_name = "success_status_label"
    hp.update_widget_style(widget, object_name)


class QtSystemSummaryWidget(QWidget):
    """System information."""

    _update_gpu: bool = True

    def __init__(self, parent: QWidget | None = None):
        QWidget.__init__(self, parent)

        # CPU summary
        self.group_box_layout = hp.make_form_layout(parent=self, spacing=1)
        self.group_box_layout.addRow(hp.make_h_line_with_text("CPU Summary"))

        # CPU freq
        self.cpu_freq_stats_label = QLabel("", self)
        self.group_box_layout.addRow("Current CPU frequency:", self.cpu_freq_stats_label)
        # Number of cores
        self.nb_cores_label = QLabel("", self)
        self.group_box_layout.addRow("Number of CPU cores:", self.nb_cores_label)
        self.cpu_load_label0 = QLabel("", self)
        self.group_box_layout.addRow("CPU load over last 1 min:", self.cpu_load_label0)
        self.cpu_load_label1 = QLabel("", self)
        self.group_box_layout.addRow("CPU load over last 5 min:", self.cpu_load_label1)
        self.cpu_load_label2 = QLabel("", self)
        self.group_box_layout.addRow("CPU load over last 15 min:", self.cpu_load_label2)

        # Memory summary
        self.group_box_layout.addRow(hp.make_h_line_with_text("Memory Summary"))
        virtual = psutil.virtual_memory()
        available = virtual.available
        total = virtual.total

        try:
            mem = psutil.Process().memory_info().rss
        except Exception:
            mem = 0
        self.process_memory_label = QLabel(f"{human_readable_byte_size(mem)}, ({round(100 * mem / total, 2)}%)", self)
        self.group_box_layout.addRow("App Memory:", self.process_memory_label)
        style_if(self.process_memory_label, mem, MEM_USAGE_ERROR, MEM_USAGE_WARNING, less=False)

        self.free_memory_label = QLabel(
            f"{human_readable_byte_size(available)}, ({round(100 * available / total, 2)}%)", self
        )
        self.group_box_layout.addRow("Free Memory:", self.free_memory_label)
        style_if(self.free_memory_label, available, MEM_ERROR, MEM_WARNING)

        self.total_memory_label = QLabel(f"{human_readable_byte_size(total)}", self)
        self.group_box_layout.addRow("Total Memory:", self.total_memory_label)
        style_if(self.total_memory_label, total, MEM_ERROR, MEM_WARNING)

        # GPU summary
        self.group_box_layout.addRow(hp.make_h_line_with_text("GPU Summary"))

        try:
            cuda_gpu_name = numba.cuda.get_current_device().name.decode()
        except CudaSupportError:
            cuda_gpu_name = "N/A"

        self.cuda_gpu_label = QLabel(f"{cuda_gpu_name}", self)
        self.group_box_layout.addRow("CUDA GPU:", self.cuda_gpu_label)

        hp.set_object_name(
            self.cuda_gpu_label, object_name="success_status_label" if cuda_gpu_name != "N/A" else "error_status_label"
        )

        self.cudatoolkit_label = QLabel("", self)
        self.group_box_layout.addRow("CUDA Toolkit:", self.cudatoolkit_label)
        self.gpu_memory_free_label = QLabel("", self)
        self.group_box_layout.addRow("Free GPU Memory:", self.gpu_memory_free_label)
        self.gpu_memory_total_label = QLabel("", self)
        self.group_box_layout.addRow("Total GPU Memory:", self.gpu_memory_total_label)

        hp.make_periodic_timer(self, self.update_all, delay=5000, start=True)
        self.update_all()

    def update_all(self) -> None:
        """Update all stats."""
        self.update_cpu()
        self.update_mem()
        self.update_gpu()

    def update_cpu(self) -> None:
        """Update CPU stats."""
        with suppress(FileNotFoundError):
            cpu = round(psutil.cpu_freq().current, 2)
        cpu = f"{cpu} Mhz" if cpu else "N/A"
        self.cpu_freq_stats_label.setText(f"{cpu}")

        # Number of cores
        n_cpu = os.cpu_count() or 1
        self.nb_cores_label.setText(f"{n_cpu // 2}")
        style_if(self.nb_cores_label, n_cpu // 2, CPU_N_ERROR, CPU_N_WARNING)

        cpu_load_values = [(elem * 16) for elem in psutil.getloadavg()]
        cpu_1min = "100.0+" if cpu_load_values[0] >= 100.0 else round(cpu_load_values[0], 2)
        self.cpu_load_label0.setText(f"{cpu_1min}%")
        cpu_5min = "100.0+" if cpu_load_values[1] >= 100.0 else round(cpu_load_values[1], 2)
        self.cpu_load_label1.setText(f"{cpu_5min}%")
        cpu_15min = "100.0+" if cpu_load_values[2] >= 100.0 else round(cpu_load_values[2], 2)
        self.cpu_load_label2.setText(f"{cpu_15min}%")

        style_if(self.cpu_load_label0, cpu_load_values[0], CPU_PERCENT_ERROR, CPU_PERCENT_WARNING)
        style_if(self.cpu_load_label1, cpu_load_values[1], CPU_PERCENT_ERROR, CPU_PERCENT_WARNING)
        style_if(self.cpu_load_label2, cpu_load_values[2], CPU_PERCENT_ERROR, CPU_PERCENT_WARNING)

    def update_mem(self) -> None:
        """Update memory stats."""
        virtual = psutil.virtual_memory()
        available = virtual.available
        total = virtual.total

        try:
            mem = psutil.Process().memory_info().rss
        except Exception:
            mem = 0
        self.process_memory_label.setText(f"{human_readable_byte_size(mem)}, ({round(100 * mem / total, 2)}%)")
        style_if(self.process_memory_label, mem, MEM_USAGE_ERROR, MEM_USAGE_WARNING, less=False)

        self.free_memory_label.setText(f"{human_readable_byte_size(available)}, ({round(100 * available / total, 2)}%)")
        style_if(self.free_memory_label, available, MEM_ERROR, MEM_WARNING)

        self.total_memory_label.setText(f"{human_readable_byte_size(total)}")
        style_if(self.total_memory_label, total, MEM_ERROR, MEM_WARNING)

    def update_gpu(self) -> None:
        """Update GPU stats."""
        # cuda_toolkit = numba.cuda.cudadrv.nvvm.is_available()
        # self.cudatoolkit_label.setText(f"{'present' if cuda_toolkit else 'absent'}")
        # if numba.cuda.cudadrv.nvvm.is_available():
        #     self.cudatoolkit_label.setStyleSheet("QLabel {color: green;}")
        # else:
        #     self.cudatoolkit_label.setStyleSheet("QLabel {color: red;}")

        if not self._update_gpu:
            return

        try:
            cuda_memory_free = numba.cuda.current_context().get_memory_info().free
            cuda_memory_total = numba.cuda.current_context().get_memory_info().total
        except CudaSupportError:
            cuda_memory_free = 0
            cuda_memory_total = 0
            self._update_gpu = False

        self.gpu_memory_free_label.setText(f"{human_readable_byte_size(cuda_memory_free)}")
        self.gpu_memory_total_label.setText(f"{human_readable_byte_size(cuda_memory_total)}")
        if cuda_memory_total == 0:
            hp.set_object_name(
                self.gpu_memory_total_label, self.gpu_memory_free_label, object_name="error_status_label"
            )
        else:
            if numba.cuda.current_context().get_memory_info().total < 8000000000:
                hp.set_object_name(self.gpu_memory_free_label, object_name="warning_status_label")
            else:
                hp.set_object_name(self.gpu_memory_free_label, object_name="success_status_label")

            if cuda_memory_free / cuda_memory_total < 0.4:
                hp.set_object_name(self.gpu_memory_free_label, object_name="error_status_label")
            elif cuda_memory_free / cuda_memory_total < 0.8:
                hp.set_object_name(self.gpu_memory_free_label, object_name="warning_status_label")
            else:
                hp.set_object_name(self.gpu_memory_free_label, object_name="success_status_label")


class SystemSummaryPopup(QtFramelessPopup):
    """Show summary of the system."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)

    def make_panel(self) -> QVBoxLayout:
        """Create widget."""
        layout = hp.make_v_layout(spacing=0, margin=0)
        layout.addWidget(QtSystemSummaryWidget(self), stretch=True)
        return layout


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    def _make_popup():
        """Create a popup."""
        popup = SystemSummaryPopup(frame)
        popup.exec()

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)

    ha.addWidget(QtSystemSummaryWidget(parent=frame))
    ha.addWidget(hp.make_btn(parent=frame, text="Open popup", func=_make_popup))

    frame.show()
    sys.exit(app.exec_())
