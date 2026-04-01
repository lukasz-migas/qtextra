"""README showcase for a range of qtextra widgets."""

from __future__ import annotations

import numpy as np
import pandas as pd
from qtpy.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra._example_helpers import divider, section
from qtextra.config import THEMES
from qtextra.dialogs.qt_confirm import QtConfirmWithTextDialog
from qtextra.widgets.qt_button_icon import QtImageButton, QtLockButton, QtMaskButton, QtPinButton, QtThemeButton
from qtextra.widgets.qt_button_tag import QtTagManager
from qtextra.widgets.qt_collapsible import QtCheckCollapsible
from qtextra.widgets.qt_combobox_color import QtColorSwatchComboBox
from qtextra.widgets.qt_combobox_multi import QtMultiSelectComboBox
from qtextra.widgets.qt_combobox_search import QtSearchableComboBox, QtSearchComboBox
from qtextra.widgets.qt_label_icon import QtPulsingAttentionLabel, QtQtaLabel
from qtextra.widgets.qt_progress_step import QtStepProgressBar
from qtextra.widgets.qt_table_view_array import QtArrayTableView
from qtextra.widgets.qt_table_view_dataframe import QtDataFrameWidget
from qtextra.widgets.qt_toggle_group import QtToggleGroup
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar


def _make_overview_tab() -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)

    layout.addWidget(section("Workflow"))
    steps = QtStepProgressBar()
    steps.labels = ["Source", "Validate", "Review", "Export", "Done"]
    steps.value = 3
    layout.addWidget(steps)

    layout.addWidget(divider())
    layout.addWidget(section("Filters"))

    toggle_group = QtToggleGroup(
        None,
        ["Recent", "Errors", "Warnings", "Pinned"],
        exclusive=False,
        value=["Recent", "Pinned"],
    )
    layout.addWidget(toggle_group)

    tags = QtTagManager(allow_action=True, flow=True)
    tags.add_tags(["Project A", "Needs review", "High priority", "Backend", "UI"])
    tags.add_tag("Assigned", active=True, allow_action=False)
    tags.add_filter(placeholder="Filter tags...", max_width=180)
    tags.add_plus()
    layout.addWidget(tags)

    layout.addWidget(divider())
    layout.addWidget(section("Details"))

    details = QtCheckCollapsible("Advanced settings", icon="settings", warning_icon=("warning", {"color": "orange"}))
    details.warning_label.setToolTip("One of the hidden settings still needs confirmation.")
    details.addRow(QLabel("Retries"))
    details.addRow(hp.make_line_edit(details, text="3"))
    details.addRow(QLabel("Destination"))
    details.addRow(hp.make_line_edit(details, text="docs/build"))
    details.addRow(QPushButton("Run preview"))
    details.expand(animate=False)
    layout.addWidget(details)
    layout.addStretch(1)
    return tab


def _make_inputs_tab(window: QWidget) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)

    layout.addWidget(section("Buttons and status"))
    button_grid = QGridLayout()
    button_grid.setHorizontalSpacing(14)
    button_grid.setVerticalSpacing(10)
    layout.addLayout(button_grid)

    button_grid.addWidget(QLabel("QtButtonIcon"), 0, 0)
    icon_row = QWidget()
    icon_row_layout = hp.make_h_layout(parent=icon_row, margin=0, spacing=6)
    for klass in (QtImageButton, QtLockButton, QtThemeButton, QtPinButton, QtMaskButton):
        btn = klass(icon_row, auto_connect=True)
        btn.set_large()
        icon_row_layout.addWidget(btn)
    button_grid.addWidget(icon_row, 0, 1)

    button_grid.addWidget(QLabel("QtLabelIcon"), 1, 0)
    label_row = QWidget()
    label_row_layout = hp.make_h_layout(parent=label_row, margin=0, spacing=10)
    static_label = QtQtaLabel(large=True)
    static_label.set_qta("info", color=THEMES.get_hex_color("icon"))
    label_row_layout.addWidget(static_label)
    warning_label = QtPulsingAttentionLabel(
        qta_name="warning",
        color_from_key="warning",
        color_to_key="icon",
        interval=1200,
    )
    label_row_layout.addWidget(warning_label)
    label_row_layout.addStretch(1)
    button_grid.addWidget(label_row, 1, 1)

    button_grid.addWidget(QLabel("QtNotificationBadge"), 2, 0)
    badge_row = QWidget()
    badge_row_layout = hp.make_h_layout(parent=badge_row, margin=0, spacing=16)
    sync_button = QPushButton("Sync queue", parent=badge_row)
    sync_button.setMinimumWidth(150)
    badge_row_layout.addWidget(sync_button)
    hp.make_notification_badge(parent=window, widget=sync_button, state="success", mode="count", size="md", count=4)

    bell = QtQtaLabel(large=True, parent=badge_row)
    bell.set_qta("notified", color=THEMES.get_hex_color("icon"))
    badge_row_layout.addWidget(bell)
    hp.make_notification_badge(parent=window, widget=bell, state="warning", mode="dot", size="sm")
    badge_row_layout.addStretch(1)
    button_grid.addWidget(badge_row, 2, 1)

    layout.addWidget(divider())
    layout.addWidget(section("Comboboxes"))

    combo_grid = QGridLayout()
    combo_grid.setHorizontalSpacing(14)
    combo_grid.setVerticalSpacing(10)
    layout.addLayout(combo_grid)

    combo_grid.addWidget(QLabel("QtSearchableComboBox"), 0, 0)
    searchable_combo = QtSearchableComboBox(window)
    searchable_combo.addItems(
        ["Alpha project", "Beta release", "Critical bugfix", "Design review", "Docs pass", "Nightly build"]
    )
    searchable_combo.setCurrentText("Design review")
    combo_grid.addWidget(searchable_combo, 0, 1)

    combo_grid.addWidget(QLabel("QtSearchComboBox"), 1, 0)
    search_combo = QtSearchComboBox(parent=window)
    search_combo.addItems(
        ["Alpha project", "Beta release", "Critical bugfix", "Design review", "Docs pass", "Nightly build"]
    )
    search_combo.set_current_text("Docs pass")
    combo_grid.addWidget(search_combo, 1, 1)

    combo_grid.addWidget(QLabel("QtColorSwatchComboBox"), 2, 0)
    color_combo = QtColorSwatchComboBox(parent=window)
    color_combo.add_swatches(
        [
            ("#0B84F3", "Blue"),
            ("#12B886", "Teal"),
            ("#FF922B", "Orange"),
            ("#FA5252", "Red"),
            ("#7C4DFF", "Violet"),
            ("#2B2D42", "Ink"),
        ],
    )
    color_combo._on_select(color_combo._panel._cells[1]._color, "Teal")
    combo_grid.addWidget(color_combo, 2, 1)

    combo_grid.addWidget(QLabel("QtMultiSelectComboBox"), 3, 0)
    multi_combo = QtMultiSelectComboBox(
        items=["UI", "Backend", "Docs", "Tests", "Release", "Design"],
        parent=window,
    )
    multi_combo.set_selected(["UI", "Docs", "Release"])
    combo_grid.addWidget(multi_combo, 3, 1)
    layout.addStretch(1)
    return tab


def _make_tables_tab() -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)

    layout.addWidget(section("Array table"))
    array_table = QtArrayTableView(sortable=True)
    data = np.array(
        [
            [1.1, 0.2, -0.4, 2.3],
            [0.9, -1.2, 1.4, 0.3],
            [1.7, 0.1, -0.8, 1.0],
            [-0.2, 0.5, 0.9, -1.1],
            [0.4, 1.6, -0.1, 0.8],
        ],
    )
    array_table.set_data(data, fmt="{:.2f}", colormap="coolwarm", min_val=-2, max_val=2)
    array_table.setMinimumHeight(210)
    layout.addWidget(array_table)

    layout.addWidget(divider())
    layout.addWidget(section("DataFrame table"))
    frame = pd.DataFrame(
        {
            "project": ["alpha", "beta", "gamma", "delta"],
            "status": ["ready", "review", "blocked", "done"],
            "score": [91.4, 84.0, 72.2, 97.3],
            "owner": ["ana", "ben", "chi", "dev"],
        },
    )
    dataframe_widget = QtDataFrameWidget(None, frame)
    dataframe_widget.setMinimumHeight(250)
    layout.addWidget(dataframe_widget)
    return tab


def _make_tools_tab(window: QWidget) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)

    layout.addWidget(section("Toolbar"))
    toolbar = QtMiniToolbar(tab, orientation="horizontal", add_spacer=False)
    for icon in ["home", "settings", "help", "info", "warning", "error"]:
        toolbar.add_qta_tool(icon, tooltip=icon, func=None)
    toolbar.add_separator()
    toolbar.add_qta_tool("color_palette", tooltip="color palette", func=None)
    layout.addWidget(toolbar)

    layout.addWidget(divider())
    layout.addWidget(section("Dialogs"))
    layout.addWidget(QLabel("Launch a couple of application dialogs from here to inspect their styling and behavior."))

    dialog_row = QWidget()
    dialog_layout = hp.make_h_layout(parent=dialog_row, margin=0, spacing=8)

    def _open_confirm_dialog() -> None:
        dialog = QtConfirmWithTextDialog(
            window,
            title="Confirm publish",
            message="Please type <b>publish</b> to continue.",
            request="publish",
        )
        THEMES.apply(dialog)
        dialog.show()
        window._showcase_dialogs.append(dialog)

    preview_btn = QPushButton("Open confirm dialog")
    preview_btn.clicked.connect(_open_confirm_dialog)
    dialog_layout.addWidget(preview_btn)
    dialog_layout.addWidget(QPushButton("Theme editor"))
    dialog_layout.addWidget(QPushButton("Logger"))
    dialog_layout.addStretch(1)
    layout.addWidget(dialog_row)

    layout.addWidget(divider())
    layout.addWidget(section("Summary"))
    summary = QLabel(
        "This tabbed showcase is intended as a broad interactive sampler. "
        "The capture script composites the tabs into the README image."
    )
    summary.setWordWrap(True)
    layout.addWidget(summary)
    layout.addStretch(1)
    return tab


def build_showcase() -> QWidget:
    """Build the tabbed showcase window."""
    widget = QWidget()
    widget.setWindowTitle("qtextra showcase")
    widget.setMinimumSize(700, 700)
    widget._showcase_dialogs = []
    THEMES.apply(widget)

    layout = QVBoxLayout(widget)
    layout.setSpacing(10)

    header = QLabel("qtextra showcase")
    header_font = header.font()
    header_font.setPointSizeF(header_font.pointSizeF() + 3)
    header_font.setBold(True)
    header.setFont(header_font)
    layout.addWidget(header)

    tabs = QTabWidget(widget)
    tabs.addTab(_make_overview_tab(), "Overview")
    tabs.addTab(_make_inputs_tab(widget), "Inputs")
    tabs.addTab(_make_tables_tab(), "Tables")
    tabs.addTab(_make_tools_tab(widget), "Tools")
    layout.addWidget(tabs)

    widget._showcase_tabs = tabs
    return widget


def main() -> int:
    """Run the showcase example."""
    app = QApplication.instance() or QApplication([])
    widget = build_showcase()
    widget.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
