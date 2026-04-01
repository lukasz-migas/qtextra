"""Compare checkable table implementations side by side."""

from __future__ import annotations

from time import perf_counter

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_table_view_check import QtCheckableTableView
from qtextra.widgets.qt_table_view_sort_check import QtProxySortCheckableTableView

CITIES = ["Berlin", "Paris", "London", "Tokyo", "Lisbon", "Oslo", "Boston", "Athens"]
ICON_OPTIONS = ["info", "success", "warning", "bug", "star", "marker"]
COLORS = ["#ef476f", "#118ab2", "#06d6a0", "#ffd166", "#8338ec", "#ff7f50", "#4cc9f0", "#8ac926"]
ROW_COUNT = 2000


def _make_config() -> TableConfig:
    return (
        TableConfig(text_alignment="left")
        .add("", "check", dtype="bool")
        .add("Name", "name", resizable=True)
        .add("City", "city")
        .add("Score", "score")
        .add("Active", "active", dtype="bool", checkable=True)
        .add("Icon", "icon", dtype="icon", sizing="contents")
        .add("Color", "color", is_color=True, sizing="contents")
    )


def _make_rows(n_rows: int = ROW_COUNT) -> list[list]:
    rows = []
    for index in range(n_rows):
        rows.append(
            [
                index % 3 == 0,
                f"Sample {index:05d}",
                CITIES[index % len(CITIES)],
                (index * 17) % 101,
                index % 4 != 0,
                ICON_OPTIONS[index % len(ICON_OPTIONS)],
                COLORS[index % len(COLORS)],
            ],
        )
    return rows


def _sync_view(table) -> None:
    table.viewport().update()
    app.processEvents()


app = QApplication([])

widget = QWidget()
THEMES.apply(widget)
widget.setWindowTitle("QtCheckableTableView Comparison")

layout = QVBoxLayout(widget)

intro = QLabel(
    "Compare the original in-model sorting table with the proxy-sorting version. "
    f"Both load {ROW_COUNT} rows and run the same action on button click."
)
summary = QLabel("Trigger an action to compare elapsed times.")

controls = QGridLayout()
controls.setHorizontalSpacing(12)
controls.setVerticalSpacing(8)

sort_name_button = QPushButton("Sort Name Asc")
sort_score_button = QPushButton("Sort Score Desc")
check_all_button = QPushButton("Check All")
uncheck_all_button = QPushButton("Uncheck All")
reload_button = QPushButton(f"Reload {ROW_COUNT} Rows")

tables_layout = QHBoxLayout()

left_panel = QVBoxLayout()
left_title = QLabel("QtCheckableTableView")
left_time = QLabel("Last operation: -")
left_status = QLabel()
left_table = QtCheckableTableView(widget, config=_make_config(), enable_all_check=True, sortable=True)

right_panel = QVBoxLayout()
right_title = QLabel("QtProxySortCheckableTableView")
right_time = QLabel("Last operation: -")
right_status = QLabel()
right_table = QtProxySortCheckableTableView(widget, config=_make_config(), enable_all_check=True, sortable=True)


def _update_status() -> None:
    right_visible_model = right_table.proxy_model() or right_table.model()
    right_visible_rows = right_visible_model.rowCount() if right_visible_model is not None else 0
    left_status.setText(
        f"Rows: {left_table.n_rows}. Checked: {len(left_table.get_all_checked())}. "
        f"Unchecked: {len(left_table.get_all_unchecked())}."
    )
    right_status.setText(
        f"Source rows: {right_table.n_rows}. Visible rows: {right_visible_rows}. "
        f"Checked: {len(right_table.get_all_checked())}. Unchecked: {len(right_table.get_all_unchecked())}."
    )


def _time_operation(label: str, table, callback, timing_label: QLabel) -> float:
    start = perf_counter()
    callback()
    _sync_view(table)
    elapsed_ms = (perf_counter() - start) * 1000.0
    timing_label.setText(f"Last operation: {label} in {elapsed_ms:.2f} ms")
    return elapsed_ms


def _run_comparison(label: str, left_callback, right_callback) -> None:
    left_ms = _time_operation(label, left_table, left_callback, left_time)
    right_ms = _time_operation(label, right_table, right_callback, right_time)
    delta = left_ms - right_ms
    faster = "proxy-sorting" if right_ms < left_ms else "original" if left_ms < right_ms else "tie"
    summary.setText(
        f"{label}: original {left_ms:.2f} ms, proxy-sorting {right_ms:.2f} ms, delta {delta:+.2f} ms, faster: {faster}."
    )
    _update_status()


sort_name_button.clicked.connect(
    lambda: _run_comparison(
        "Sort Name Asc",
        lambda: left_table.model().sort(1, Qt.SortOrder.AscendingOrder),
        lambda: right_table.proxy_model().sort(1, Qt.SortOrder.AscendingOrder),
    ),
)
sort_score_button.clicked.connect(
    lambda: _run_comparison(
        "Sort Score Desc",
        lambda: left_table.model().sort(3, Qt.SortOrder.DescendingOrder),
        lambda: right_table.proxy_model().sort(3, Qt.SortOrder.DescendingOrder),
    ),
)
check_all_button.clicked.connect(
    lambda: _run_comparison(
        "Check All",
        left_table.check_all_rows,
        right_table.check_all_rows,
    ),
)
uncheck_all_button.clicked.connect(
    lambda: _run_comparison(
        "Uncheck All",
        left_table.uncheck_all_rows,
        right_table.uncheck_all_rows,
    ),
)


def _reload_both() -> None:
    rows = _make_rows()
    left_table.reset_data()
    left_table.add_data([row[:] for row in rows])
    right_table.reset_data()
    right_table.add_data([row[:] for row in rows])
    proxy = right_table.proxy_model()
    if proxy is not None:
        proxy.sort(1, Qt.SortOrder.AscendingOrder)
    left_table.select_row(0)
    right_table.select_row(0)


def _reload_comparison() -> None:
    rows = _make_rows()

    left_ms = _time_operation(
        f"Reload {ROW_COUNT} Rows",
        left_table,
        lambda: (
            left_table.reset_data(),
            left_table.add_data([row[:] for row in rows]),
            left_table.select_row(0),
        ),
        left_time,
    )
    right_ms = _time_operation(
        f"Reload {ROW_COUNT} Rows",
        right_table,
        lambda: (
            right_table.reset_data(),
            right_table.add_data([row[:] for row in rows]),
            right_table.proxy_model().sort(1, Qt.SortOrder.AscendingOrder),
            right_table.select_row(0),
        ),
        right_time,
    )
    delta = left_ms - right_ms
    faster = "proxy-sorting" if right_ms < left_ms else "original" if left_ms < right_ms else "tie"
    summary.setText(
        f"Reload {ROW_COUNT} Rows: original {left_ms:.2f} ms, proxy-sorting {right_ms:.2f} ms, "
        f"delta {delta:+.2f} ms, faster: {faster}."
    )
    _update_status()


reload_button.clicked.connect(_reload_comparison)

controls.addWidget(sort_name_button, 0, 0)
controls.addWidget(sort_score_button, 0, 1)
controls.addWidget(check_all_button, 0, 2)
controls.addWidget(uncheck_all_button, 0, 3)
controls.addWidget(reload_button, 0, 4)

left_panel.addWidget(left_title)
left_panel.addWidget(left_time)
left_panel.addWidget(left_status)
left_panel.addWidget(left_table)

right_panel.addWidget(right_title)
right_panel.addWidget(right_time)
right_panel.addWidget(right_status)
right_panel.addWidget(right_table)

tables_layout.addLayout(left_panel)
tables_layout.addLayout(right_panel)

layout.addWidget(intro)
layout.addWidget(summary)
layout.addLayout(controls)
layout.addLayout(tables_layout)

_reload_both()
_update_status()

widget.resize(1480, 760)
widget.show()

app.exec_()
