"""README showcase for a few qtextra widgets."""

from qtpy.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra._example_helpers import divider, section
from qtextra.config import THEMES
from qtextra.widgets.qt_button_icon import QtImageButton, QtLockButton, QtMaskButton, QtPinButton, QtThemeButton
from qtextra.widgets.qt_button_tag import QtTagManager
from qtextra.widgets.qt_collapsible import QtCheckCollapsible
from qtextra.widgets.qt_combobox_color import QtColorSwatchComboBox
from qtextra.widgets.qt_combobox_multi import QtMultiSelectComboBox
from qtextra.widgets.qt_combobox_search import QtSearchableComboBox, QtSearchComboBox
from qtextra.widgets.qt_label_icon import QtPulsingAttentionLabel, QtQtaLabel
from qtextra.widgets.qt_progress_step import QtStepProgressBar
from qtextra.widgets.qt_toggle_group import QtToggleGroup

app = QApplication([])

widget = QWidget()
widget.setWindowTitle("qtextra showcase")
widget.setMinimumSize(1100, 860)
THEMES.apply(widget)

layout = QVBoxLayout(widget)
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
    qta_name="warning", color_from_key="warning", color_to_key="icon", interval=1200
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
hp.make_notification_badge(parent=badge_row, widget=sync_button, state="success", mode="count", size="lg", count=4)

bell = QtQtaLabel(large=True, parent=badge_row)
bell.set_qta("notified", color=THEMES.get_hex_color("icon"))
badge_row_layout.addWidget(bell)
hp.make_notification_badge(parent=badge_row, widget=bell, state="warning", mode="dot", size="sm")
badge_row_layout.addStretch(1)
button_grid.addWidget(badge_row, 2, 1)

layout.addWidget(divider())
layout.addWidget(section("Comboboxes"))

combo_grid = QGridLayout()
combo_grid.setHorizontalSpacing(14)
combo_grid.setVerticalSpacing(10)
layout.addLayout(combo_grid)

combo_grid.addWidget(QLabel("QtSearchableComboBox"), 0, 0)
search_combo = QtSearchableComboBox(widget)
search_combo.addItems(
    ["Alpha project", "Beta release", "Critical bugfix", "Design review", "Docs pass", "Nightly build"]
)
search_combo.setCurrentText("Design review")
combo_grid.addWidget(search_combo, 0, 1)

combo_grid.addWidget(QLabel("QtSearchComboBox"), 1, 0)
search_combo = QtSearchComboBox(parent=widget)
search_combo.addItems(
    ["Alpha project", "Beta release", "Critical bugfix", "Design review", "Docs pass", "Nightly build"]
)
combo_grid.addWidget(search_combo, 1, 1)

combo_grid.addWidget(QLabel("QtColorSwatchComboBox"), 2, 0)
color_combo = QtColorSwatchComboBox(parent=widget)
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
    parent=widget,
)
multi_combo.set_selected(["UI", "Docs", "Release"])
combo_grid.addWidget(multi_combo, 3, 1)

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
widget.show()

app.exec_()
