"""QtCheckableTableView."""

from __future__ import annotations

from qtpy.QtCore import QModelIndex, Qt
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
from qtextra.widgets.qt_table_view_check import QtCheckableTableView

ICON_COLUMN = 5
COLOR_COLUMN = 6
ALIGNMENTS = {
    "Left": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    "Center": Qt.AlignmentFlag.AlignCenter,
    "Right": Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
}
ICON_OPTIONS = ["info", "success", "warning", "bug", "star", "marker"]


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


def _make_rows() -> list[list]:
    return [
        [True, "Alice", "Berlin", 92, True, "success", "#ef476f"],
        [False, "Bob", "Paris", 78, False, "info", "#118ab2"],
        [True, "Carol", "London", 85, True, "star", "#06d6a0"],
        [False, "Dave", "Tokyo", 60, False, "warning", "#ffd166"],
        [True, "Eve", "Lisbon", 99, True, "bug", "#8338ec"],
    ]


def _emit_full_data_change(table: QtCheckableTableView) -> None:
    model = table.model()
    if model.rowCount() == 0 or model.columnCount() == 0:
        return
    top_left = model.index(0, 0)
    bottom_right = model.index(model.rowCount() - 1, model.columnCount() - 1)
    model.dataChanged.emit(top_left, bottom_right)
    table.viewport().update()


def _current_row(table: QtCheckableTableView) -> int:
    row = table.currentIndex().row()
    return max(row, 0)


app = QApplication([])

widget = QWidget()
THEMES.apply(widget)
widget.setWindowTitle("QtCheckableTableView Example")

layout = QVBoxLayout(widget)

status = QLabel()
selection_label = QLabel("Double-click a color swatch to edit it, or use the controls below.")

table = QtCheckableTableView(widget, config=_make_config(), enable_all_check=True)
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
check_all_button = QPushButton("Check All")
uncheck_all_button = QPushButton("Uncheck All")
reload_button = QPushButton("Reload Data")


def _update_labels() -> None:
    row = _current_row(table)
    row_data = table.get_row_data(row) if table.n_rows else []
    selected_name = row_data[1] if len(row_data) > 1 else "None"
    selected_icon = row_data[ICON_COLUMN] if len(row_data) > ICON_COLUMN else "-"
    selected_color = row_data[COLOR_COLUMN] if len(row_data) > COLOR_COLUMN else "-"
    status.setText(
        f"{table.n_rows} rows loaded. Checked: {len(table.get_all_checked())}. "
        f"Unchecked: {len(table.get_all_unchecked())}. Visible: {len(table.get_all_shown())}."
    )
    selection_label.setText(f"Selected row: {row} ({selected_name}). Icon: {selected_icon}. Color: {selected_color}.")
    if selected_icon in ICON_OPTIONS:
        icon_combo.setCurrentText(selected_icon)


def _apply_alignment(text: str) -> None:
    table.model().text_alignment = ALIGNMENTS[text]
    _emit_full_data_change(table)


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
    next_score = int(table.get_value(3, row)) + 7
    next_score = 55 if next_score > 100 else next_score
    next_color = ["#ef476f", "#118ab2", "#06d6a0", "#ffd166", "#8338ec", "#ff7f50"][row % 6]
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
    table.select_row(0)
    _update_labels()


def _sync_on_selection(*_args) -> None:
    _update_labels()


def _handle_double_click(index: QModelIndex) -> None:
    if index.column() != COLOR_COLUMN:
        _sync_on_selection()
        return
    table.select_row(index.row(), match_to_sort=False)
    _pick_color(index.row())


alignment_combo.currentTextChanged.connect(_apply_alignment)
icon_combo.currentTextChanged.connect(_apply_icon)
recolor_button.clicked.connect(lambda: _pick_color())
randomize_button.clicked.connect(_randomize_row)
check_all_button.clicked.connect(table.check_all_rows)
check_all_button.clicked.connect(_update_labels)
uncheck_all_button.clicked.connect(table.uncheck_all_rows)
uncheck_all_button.clicked.connect(_update_labels)
reload_button.clicked.connect(_reload)
table.clicked.connect(_sync_on_selection)
table.doubleClicked.connect(_handle_double_click)
table.selectionModel().selectionChanged.connect(_sync_on_selection)

controls.addWidget(QLabel("Alignment"), 0, 0)
controls.addWidget(alignment_combo, 0, 1)
controls.addWidget(QLabel("Selected Row Icon"), 0, 2)
controls.addWidget(icon_combo, 0, 3)
controls.addWidget(recolor_button, 1, 0, 1, 2)
controls.addWidget(randomize_button, 1, 2, 1, 2)

actions = QHBoxLayout()
actions.addWidget(check_all_button)
actions.addWidget(uncheck_all_button)
actions.addWidget(reload_button)

layout.addWidget(status)
layout.addWidget(selection_label)
layout.addLayout(controls)
layout.addWidget(table)
layout.addLayout(actions)

_update_labels()

widget.resize(1040, 560)
widget.show()

app.exec_()
