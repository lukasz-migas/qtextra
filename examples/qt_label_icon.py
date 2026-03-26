"""QtQtaLabel."""

from qtpy.QtWidgets import QApplication, QWidget

from qtextra.assets import QTA_MAPPING, get_icon
from qtextra.config import THEMES
from qtextra.widgets.qt_label_icon import QtPulsingAttentionLabel, QtQtaLabel, QtWarningPulseLabel
from qtextra.widgets.qt_layout_flow import QtAnimatedFlowLayout

app = QApplication([])

widget = QWidget()
widget.setMinimumWidth(800)
widget.setMaximumHeight(600)
THEMES.apply(widget)

layout = QtAnimatedFlowLayout(use_animation=True)
layout.setVerticalSpacing(2)
layout.setHorizontalSpacing(2)
widget.setLayout(layout)

layout.addWidget(QtWarningPulseLabel(interval=1000))

# Pulsing attention labels — color transitions every 1 s
for qta_name, theme_color in [
    ("warning", "warning"),
    ("error", "error"),
    ("info", "success"),
]:
    label = QtPulsingAttentionLabel(
        qta_name=qta_name,
        color_from=THEMES.get_hex_color(theme_color),
        color_to=THEMES.get_hex_color("icon"),
        interval=1000,
    )
    label.setToolTip(f"Pulsing attention — {qta_name}")
    layout.addWidget(label)

for name in QTA_MAPPING:
    qta_name, qta_kws = get_icon(name)
    label = QtQtaLabel()
    label.set_qta(qta_name, **qta_kws)
    label.setToolTip(f"{name} :: {qta_name}")
    label.set_large()
    layout.addWidget(label)

widget.show()

app.exec_()
