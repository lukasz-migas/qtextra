"""QtProxySortCheckableTableView."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qtextra.config import THEMES
from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_table_view_sort_check import QtProxySortCheckableTableView

ICON_COLUMN = 5
COLOR_COLUMN = 6
ALIGNMENTS = {
    "Left": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    "Center": Qt.AlignmentFlag.AlignCenter,
    "Right": Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
}
ICON_OPTIONS = ["info", "success", "warning", "bug", "star", "marker"]
CITIES = ["Berlin", "Paris", "London", "Tokyo", "Lisbon", "Oslo", "Boston", "Athens"]
COLORS = ["#ef476f", "#118ab2", "#06d6a0", "#ffd166", "#8338ec", "#ff7f50", "#4cc9f0", "#8ac926"]


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


def _make_rows(n_rows: int = 1500) -> list[list]:
    rows = []
    for index in range(n_rows):
        rows.append(
            [
                index % 3 == 0,
                f"Sample {index:04d}",
                CITIES[index % len(CITIES)],
                (index * 17) % 101,
                index % 4 != 0,
                ICON_OPTIONS[index % len(ICON_OPTIONS)],
                COLORS[index % len(COLORS)],
            ],
        )
    return rows


def _current_row(table: QtProxySortCheckableTableView) -> int:
    row = table.currentIndex().row()
    return max(row, 0)


app = QApplication([])

widget = QWidget()
THEMES.apply(widget)
widget.setWindowTitle("QtProxySortCheckableTableView Example")

layout = QVBoxLayout(widget)

status = QLabel()
selection_label = QLabel("Double-click a color swatch to edit it, then sort by any column header.")

table = QtProxySortCheckableTableView(widget, config=_make_config(), enable_all_check=True, sortable=True)
table.add_data(_make_rows())
table.select_row(0)

controls = QGridLayout()
controls.setHorizontalSpacing(12)
controls.setVerticalSpacing(8)

alignment_combo = QComboBox()
alignment_combo.addItems(list(ALIGNMENTS))
alignment_combo.setCurrentText("Left")

icon_combo = QComboBox()
icon_combo.addItems(ICON_OPTIONS)

recolor_button = QPushButton("Change Selected Color")
randomize_button = QPushButton("Randomize Selected Row")
sort_score_button = QPushButton("Sort Score Desc")
sort_name_button = QPushButton("Sort Name Asc")
check_all_button = QPushButton("Check All Visible")
uncheck_all_button = QPushButton("Uncheck All Visible")
reload_button = QPushButton("Reload 1500 Rows")


def _update_labels() -> None:
    row = _current_row(table)
    row_data = table.get_row_data(row) if table.n_rows else []
    selected_name = row_data[1] if len(row_data) > 1 else "None"
    selected_icon = row_data[ICON_COLUMN] if len(row_data) > ICON_COLUMN else "-"
    selected_color = row_data[COLOR_COLUMN] if len(row_data) > COLOR_COLUMN else "-"
    visible_model = table.proxy_model() or table.model()
    visible_rows = visible_model.rowCount() if visible_model is not None else 0
    status.setText(
        f"{table.n_rows} source rows loaded. Visible rows: {visible_rows}. "
        f"Checked: {len(table.get_all_checked())}. Unchecked: {len(table.get_all_unchecked())}."
    )
    selection_label.setText(
        f"Selected visible row: {row} ({selected_name}). Icon: {selected_icon}. Color: {selected_color}."
    )
    if selected_icon in ICON_OPTIONS:
        icon_combo.setCurrentText(selected_icon)


def _apply_alignment(text: str) -> None:
    table.model().text_alignment = ALIGNMENTS[text]
    source = table.model()
    if source.rowCount() and source.columnCount():
        top_left = source.index(0, 0)
        bottom_right = source.index(source.rowCount() - 1, source.columnCount() - 1)
        source.dataChanged.emit(top_left, bottom_right)
    table.viewport().update()


def _apply_icon(text: str) -> None:
    table.update_value(_current_row(table), ICON_COLUMN, text, match_to_sort=False)
    _update_labels()


def _pick_color(row: int | None = None) -> None:
    if row is None:
        row = _current_row(table)
    current = QColor(table.get_value(COLOR_COLUMN, row))
    color = QColorDialog.getColor(current, widget, "Choose Row Swatch Color")
    if not color.isValid():
        return
    table.update_value(row, COLOR_COLUMN, color.name(), match_to_sort=False)
    _update_labels()


def _randomize_row() -> None:
    row = _current_row(table)
    active = not bool(table.get_value(4, row))
    checked = not bool(table.get_value(0, row))
    next_icon = ICON_OPTIONS[(ICON_OPTIONS.index(icon_combo.currentText()) + 1) % len(ICON_OPTIONS)]
    next_score = (int(table.get_value(3, row)) + 11) % 101
    next_color = COLORS[(row + 3) % len(COLORS)]
    table.update_values(
        row,
        {
            0: checked,
            3: next_score,
            4: active,
            ICON_COLUMN: next_icon,
            COLOR_COLUMN: next_color,
        },
        match_to_sort=False,
    )
    _update_labels()


def _reload() -> None:
    table.reset_data()
    table.add_data(_make_rows())
    proxy = table.proxy_model()
    if proxy is not None:
        proxy.sort(1, Qt.SortOrder.AscendingOrder)
    table.select_row(0)
    _update_labels()


def _handle_double_click(index) -> None:
    if index.column() != COLOR_COLUMN:
        _update_labels()
        return
    table.select_row(index.row(), match_to_sort=False)
    _pick_color(index.row())


alignment_combo.currentTextChanged.connect(_apply_alignment)
icon_combo.currentTextChanged.connect(_apply_icon)
recolor_button.clicked.connect(lambda: _pick_color())
randomize_button.clicked.connect(_randomize_row)
sort_score_button.clicked.connect(lambda: table.proxy_model().sort(3, Qt.SortOrder.DescendingOrder))
sort_score_button.clicked.connect(_update_labels)
sort_name_button.clicked.connect(lambda: table.proxy_model().sort(1, Qt.SortOrder.AscendingOrder))
sort_name_button.clicked.connect(_update_labels)
check_all_button.clicked.connect(table.check_all_rows)
check_all_button.clicked.connect(_update_labels)
uncheck_all_button.clicked.connect(table.uncheck_all_rows)
uncheck_all_button.clicked.connect(_update_labels)
reload_button.clicked.connect(_reload)
table.clicked.connect(lambda *_args: _update_labels())
table.doubleClicked.connect(_handle_double_click)
table.selectionModel().selectionChanged.connect(lambda *_args: _update_labels())

controls.addWidget(QLabel("Alignment"), 0, 0)
controls.addWidget(alignment_combo, 0, 1)
controls.addWidget(QLabel("Selected Row Icon"), 0, 2)
controls.addWidget(icon_combo, 0, 3)
controls.addWidget(recolor_button, 1, 0, 1, 2)
controls.addWidget(randomize_button, 1, 2, 1, 2)

actions = QHBoxLayout()
actions.addWidget(sort_name_button)
actions.addWidget(sort_score_button)
actions.addWidget(check_all_button)
actions.addWidget(uncheck_all_button)
actions.addWidget(reload_button)

layout.addWidget(status)
layout.addWidget(selection_label)
layout.addLayout(controls)
layout.addWidget(table)
layout.addLayout(actions)

proxy = table.proxy_model()
if proxy is not None:
    proxy.sort(1, Qt.SortOrder.AscendingOrder)
_update_labels()

widget.resize(1160, 640)
widget.show()

app.exec_()
