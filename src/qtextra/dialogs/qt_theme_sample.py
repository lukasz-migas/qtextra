"""Sample widget that contains a broad mix of standard Qt and qtextra widgets."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollBar,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)
from superqt.sliders import QRangeSlider

import qtextra.helpers as hp
from qtextra.widgets.qt_button_color import ColorCircleButton
from qtextra.widgets.qt_button_progress import QtActiveProgressBarButton
from qtextra.widgets.qt_button_tag import QtTagManager
from qtextra.widgets.qt_filter_edit import QtFilterEdit
from qtextra.widgets.qt_label_read_more import QReadMoreLessLabel
from qtextra.widgets.qt_notification_badge import QtNotificationBadge
from qtextra.widgets.qt_toggle_group import QtToggleGroup

blurb = """
<h3>Heading</h3>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit,
sed do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation
ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur
sint occaecat cupidatat non proident, sunt in culpa qui
officia deserunt mollit anim id est laborum.</p>
"""

read_more_blurb = """
qtextra widgets integrate with the same bundled theme styles as the base Qt sample.
<br><br>
The preview now includes toggle groups, filters, tags, progress buttons, badges,
and color pickers so theme changes are easier to evaluate in one place.
<moreless>
You can use the sample to validate contrast, spacing, hover states, and status colors.
<split>
It is intentionally dense enough to expose weak theme choices quickly.
"""


class TabDemo(QTabWidget):
    """Demo tab."""

    def __init__(self, parent=None, emphasized=False):
        super().__init__(parent)
        self.setProperty("emphasized", emphasized)
        self.tab1 = QWidget()
        self.tab1.setProperty("emphasized", emphasized)
        self.tab2 = QWidget()
        self.tab2.setProperty("emphasized", emphasized)

        self.addTab(self.tab1, "Tab 1")
        self.addTab(self.tab2, "Tab 2")
        layout = QFormLayout()
        layout.addRow("Height", QSpinBox())
        layout.addRow("Weight", QDoubleSpinBox())
        self.setTabText(0, "Tab 1")
        self.tab1.setLayout(layout)

        layout2 = QFormLayout()
        sex = QHBoxLayout()
        sex.addWidget(QRadioButton("Male"))
        sex.addWidget(QRadioButton("Female"))
        layout2.addRow(QLabel("Sex"), sex)
        layout2.addRow("Date of Birth", QLineEdit())
        self.setTabText(1, "Tab 2")
        self.tab2.setLayout(layout2)

        self.setWindowTitle("tab demo")


class QtSampleWidget(QWidget):
    """Widget that showcases many types of Qt widgets."""

    def __init__(self, emphasized: bool = False):
        super().__init__()
        self.setProperty("emphasized", emphasized)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        qt_group = hp.make_group_box(self, "Qt Widgets", is_flat=False)
        qt_group.setLayout(self._make_qt_sample_layout(emphasized))
        main_layout.addWidget(qt_group)

        qtextra_group = hp.make_group_box(self, "qtextra Widgets", is_flat=False)
        qtextra_group.setLayout(self._make_qtextra_sample_layout())
        main_layout.addWidget(qtextra_group)

    def _make_qt_sample_layout(self, emphasized: bool) -> QVBoxLayout:
        """Build the standard Qt preview section."""
        lay = QVBoxLayout()
        lay.addWidget(QPushButton("push button"))
        box = QComboBox()
        box.addItems(["a", "b", "c", "cd"])
        lay.addWidget(box)
        lay.addWidget(QFontComboBox())

        hbox = QHBoxLayout()
        chk = QCheckBox("tristate")
        chk.setToolTip("I am a tooltip")
        chk.setTristate(True)
        chk.setCheckState(Qt.PartiallyChecked)
        chk3 = QCheckBox("checked")
        chk3.setChecked(True)
        hbox.addWidget(QCheckBox("unchecked"))
        hbox.addWidget(chk)
        hbox.addWidget(chk3)
        lay.addLayout(hbox)

        lay.addWidget(TabDemo(emphasized=emphasized))

        sld = QSlider(Qt.Orientation.Horizontal)
        sld.setValue(50)
        lay.addWidget(sld)
        scroll = QScrollBar(Qt.Orientation.Horizontal)
        scroll.setValue(50)
        lay.addWidget(scroll)
        lay.addWidget(QRangeSlider(Qt.Orientation.Horizontal, self))
        text = QTextEdit()
        text.setMaximumHeight(100)
        text.setHtml(blurb)
        lay.addWidget(text)
        lay.addWidget(QTimeEdit())
        edit = QLineEdit()
        edit.setPlaceholderText("LineEdit placeholder...")
        lay.addWidget(edit)
        lay.addWidget(QLabel("label"))

        status_layout = QHBoxLayout()
        for text, object_name in (
            ("SUCCESS", "success"),
            ("WARNING", "warning"),
            ("ACTIVE", "active"),
            ("STANDOUT", "standout"),
        ):
            label = QLabel(text)
            label.setObjectName(object_name)
            status_layout.addWidget(label)
        lay.addLayout(status_layout)

        prog = QProgressBar()
        prog.setValue(50)
        lay.addWidget(prog)

        busy = QProgressBar()
        busy.setMaximum(0)
        lay.addWidget(busy)

        group_box = QGroupBox("Exclusive Radio Buttons")
        radio1 = QRadioButton("&Radio button 1")
        radio1.setChecked(True)
        radio2 = QRadioButton("R&adio button 2")
        radio3 = QRadioButton("Ra&dio button 3")
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(radio1)
        radio_layout.addWidget(radio2)
        radio_layout.addWidget(radio3)
        radio_layout.addStretch(1)
        group_box.setLayout(radio_layout)
        lay.addWidget(group_box)

        icon_layout = QHBoxLayout()
        icon_layout.addWidget(hp.make_qta_btn(None, "fa5s.save"))
        icon_layout.addWidget(hp.make_qta_btn(None, "ei.stop-alt"))
        icon_layout.addWidget(hp.make_qta_btn(None, "fa6.heart"))
        icon_layout.addStretch(1)
        lay.addLayout(icon_layout)
        return lay

    def _make_qtextra_sample_layout(self) -> QVBoxLayout:
        """Build the qtextra preview section."""
        layout = QVBoxLayout()

        layout.addWidget(QtToggleGroup(self, ["Overview", "Details", "History"], value="Details"))

        filter_edit = QtFilterEdit(self, enable_switch=True)
        filter_edit.add_filter("status:open")
        filter_edit.add_filter("owner:me")
        layout.addWidget(filter_edit)

        tag_manager = QtTagManager(self, allow_action=True)
        tag_manager.add_tags(["Alpha", "Beta", "Gamma"], allow_action=True)
        layout.addWidget(tag_manager)

        action_row = hp.make_h_layout(spacing=6)
        notify_btn = hp.make_btn(self, "Inbox")
        action_row.addWidget(notify_btn)
        action_row.addWidget(hp.make_btn(self, "Action Required", object_name="warning_btn"))
        action_row.addStretch(1)
        layout.addLayout(action_row)

        badge = QtNotificationBadge(parent=self, widget=notify_btn, state="warning", mode="count", count=3)
        badge.raise_()
        self.notification_badge = badge

        progress_btn = QtActiveProgressBarButton(self, text="Sync project")
        progress_btn.setRange(0, 5)
        progress_btn.setValue(2)
        progress_btn.active = True
        layout.addWidget(progress_btn)

        color_row = hp.make_h_layout(
            hp.make_swatch(self, "#1ed760", tooltip="Success swatch"),
            hp.make_swatch(self, "#529eff", tooltip="Info swatch"),
            ColorCircleButton("#ff693c", parent=self),
            spacing=8,
        )
        color_row.addStretch(1)
        layout.addLayout(color_row)

        layout.addWidget(QReadMoreLessLabel(self, read_more_blurb))
        return layout
