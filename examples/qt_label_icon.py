"""QtQtaLabel"""

from qtpy.QtWidgets import QApplication, QWidget

from qtextra.assets import QTA_MAPPING, get_icon
from qtextra.config import THEMES
from qtextra.widgets.qt_label_icon import QtQtaLabel
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

for name in QTA_MAPPING.keys():
    qta_name, qta_kws = get_icon(name)
    label = QtQtaLabel()
    label.set_qta(qta_name, **qta_kws)
    label.setToolTip(f"{name} :: {qta_name}")
    label.set_large()
    layout.addWidget(label)

widget.show()

app.exec_()
