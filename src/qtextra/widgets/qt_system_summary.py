"""System summary widget."""

from __future__ import annotations

import os
from contextlib import suppress

import numba
import psutil
from koyo.utilities import human_readable_byte_size
from numba.cuda import CudaSupportError
from qtpy.QtWidgets import QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessTool

MEM_USAGE_ERROR = 4e9  # 4 GB — app is using a lot
MEM_USAGE_WARNING = 16e9  # 16 GB

MEM_ERROR = 8e9  # less than this is critically low free/total RAM
MEM_WARNING = 32e9

CPU_N_ERROR = 30
CPU_N_WARNING = 15

CPU_PERCENT_ERROR = 50
CPU_PERCENT_WARNING = 30


def style_if(widget: QWidget, value: float, error_if: float, warn_if: float, less: bool = True) -> None:
    """Apply a status object-name to *widget* based on whether *value* is above/below thresholds."""
    if less:
        object_name = (
            "error_status_label"
            if value < error_if
            else "warning_status_label"
            if value < warn_if
            else "success_status_label"
        )
    else:
        object_name = (
            "error_status_label"
            if value > error_if
            else "warning_status_label"
            if value > warn_if
            else "success_status_label"
        )
    hp.update_widget_style(widget, object_name)


class QtSystemSummaryWidget(QWidget):
    """System information summary — refreshes every 5 seconds."""

    _update_gpu: bool = True

    def __init__(self, parent: QWidget | None = None):
        QWidget.__init__(self, parent)

        layout = hp.make_form_layout(parent=self, spacing=1)

        # ── CPU ───────────────────────────────────────────────────────────────
        layout.addRow(hp.make_h_line_with_text("CPU Summary"))
        self.cpu_freq_label = hp.make_label(self, "")
        layout.addRow("Current CPU frequency:", self.cpu_freq_label)
        self.nb_cores_label = hp.make_label(self, "")
        layout.addRow("Number of CPU cores:", self.nb_cores_label)
        self.cpu_load_label0 = hp.make_label(self, "")
        layout.addRow("CPU load (last 1 min):", self.cpu_load_label0)
        self.cpu_load_label1 = hp.make_label(self, "")
        layout.addRow("CPU load (last 5 min):", self.cpu_load_label1)
        self.cpu_load_label2 = hp.make_label(self, "")
        layout.addRow("CPU load (last 15 min):", self.cpu_load_label2)

        # ── Memory ────────────────────────────────────────────────────────────
        layout.addRow(hp.make_h_line_with_text("Memory Summary"))
        self.process_memory_label = hp.make_label(self, "")
        layout.addRow("App memory:", self.process_memory_label)
        self.free_memory_label = hp.make_label(self, "")
        layout.addRow("Free memory:", self.free_memory_label)
        self.total_memory_label = hp.make_label(self, "")
        layout.addRow("Total memory:", self.total_memory_label)

        # ── GPU ───────────────────────────────────────────────────────────────
        layout.addRow(hp.make_h_line_with_text("GPU Summary"))

        try:
            cuda_gpu_name = numba.cuda.get_current_device().name.decode()
        except CudaSupportError:
            cuda_gpu_name = "N/A"

        self.cuda_gpu_label = hp.make_label(self, cuda_gpu_name)
        layout.addRow("CUDA GPU:", self.cuda_gpu_label)
        hp.set_object_name(
            self.cuda_gpu_label,
            object_name="success_status_label" if cuda_gpu_name != "N/A" else "warning_status_label",
        )

        self.gpu_memory_free_label = hp.make_label(self, "")
        layout.addRow("Free GPU memory:", self.gpu_memory_free_label)
        self.gpu_memory_total_label = hp.make_label(self, "")
        layout.addRow("Total GPU memory:", self.gpu_memory_total_label)

        hp.make_periodic_timer(self, self.update_all, delay=5000, start=True)
        self.update_all()

    def update_all(self) -> None:
        """Update all stats."""
        self.update_cpu()
        self.update_mem()
        self.update_gpu()

    def update_cpu(self) -> None:
        """Update CPU stats."""
        cpu_str = "N/A"
        with suppress(FileNotFoundError, AttributeError):
            freq = psutil.cpu_freq()
            if freq is not None:
                cpu_str = f"{round(freq.current, 2)} MHz"
        self.cpu_freq_label.setText(cpu_str)

        n_cpu = os.cpu_count() or 1
        n_physical = n_cpu // 2
        self.nb_cores_label.setText(str(n_physical))
        style_if(self.nb_cores_label, n_physical, CPU_N_ERROR, CPU_N_WARNING)

        cpu_load_values = [elem * 16 for elem in psutil.getloadavg()]
        for label, value in zip(
            (self.cpu_load_label0, self.cpu_load_label1, self.cpu_load_label2),
            cpu_load_values,
        ):
            text = "100.0+%" if value >= 100.0 else f"{round(value, 2)}%"
            label.setText(text)
            style_if(label, value, CPU_PERCENT_ERROR, CPU_PERCENT_WARNING, less=False)

    def update_mem(self) -> None:
        """Update memory stats."""
        virtual = psutil.virtual_memory()
        available = virtual.available
        total = virtual.total

        try:
            mem = psutil.Process().memory_info().rss
        except psutil.Error:
            mem = 0

        pct = round(100 * mem / total, 2) if total else 0
        self.process_memory_label.setText(f"{human_readable_byte_size(mem)} ({pct}%)")
        style_if(self.process_memory_label, mem, MEM_USAGE_ERROR, MEM_USAGE_WARNING, less=False)

        avail_pct = round(100 * available / total, 2) if total else 0
        self.free_memory_label.setText(f"{human_readable_byte_size(available)} ({avail_pct}%)")
        style_if(self.free_memory_label, available, MEM_ERROR, MEM_WARNING)

        self.total_memory_label.setText(human_readable_byte_size(total))
        style_if(self.total_memory_label, total, MEM_ERROR, MEM_WARNING)

    def update_gpu(self) -> None:
        """Update GPU memory stats."""
        if not self._update_gpu:
            return

        try:
            ctx = numba.cuda.current_context()
            mem_info = ctx.get_memory_info()
            cuda_memory_free = mem_info.free
            cuda_memory_total = mem_info.total
        except CudaSupportError:
            cuda_memory_free = 0
            cuda_memory_total = 0
            self._update_gpu = False

        self.gpu_memory_free_label.setText(human_readable_byte_size(cuda_memory_free))
        self.gpu_memory_total_label.setText(human_readable_byte_size(cuda_memory_total))

        if cuda_memory_total == 0:
            hp.set_object_name(
                self.gpu_memory_free_label,
                self.gpu_memory_total_label,
                object_name="warning_status_label",
            )
        else:
            hp.set_object_name(
                self.gpu_memory_total_label,
                object_name="warning_status_label" if cuda_memory_total < 8_000_000_000 else "success_status_label",
            )
            free_ratio = cuda_memory_free / cuda_memory_total
            hp.set_object_name(
                self.gpu_memory_free_label,
                object_name=(
                    "warning_status_label"
                    if free_ratio < 0.4
                    else "warning_status_label"
                    if free_ratio < 0.8
                    else "success_status_label"
                ),
            )


class SystemSummaryPopup(QtFramelessTool):
    """Show summary of the system."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)

    def make_panel(self):
        """Create widget."""
        layout = hp.make_v_layout(spacing=0, margin=0)
        layout.addLayout(self._make_hide_layout("System Summary"))
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
    sys.exit(app.exec())
