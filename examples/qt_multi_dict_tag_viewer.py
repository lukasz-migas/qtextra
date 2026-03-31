"""QtMultiDictTagViewer."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_multi_dict_summary import QtMultiDictSummaryWidget
from qtextra.widgets.qt_multi_dict_tag_viewer import QtMultiDictTagViewer

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

layout.addWidget(QLabel("QtMultiDictTagViewer + standalone summary"))
viewer = QtMultiDictTagViewer()
summary = QtMultiDictSummaryWidget()
viewer.evt_items_changed.connect(summary.set_items)
viewer.set_items(
    {
        "sample_a": {
            "group": "control",
            "replicate": 1,
            "score": 0.91,
        },
        "sample_b": {
            "group": "treated",
            "replicate": 2,
            "score": 0.84,
            "note": None,
        },
        "sample_c": {
            "group": "treated",
            "replicate": 3,
        },
        "sample_d": {
            "group": "treated",
            "replicate": 4,
        },
        "sample_e": {
            "group": "treated",
            "replicate": 5,
        },
        "sample_f": {
            "group": "treated",
            "replicate": 6,
        },
    },
)
body = QVBoxLayout()
body.addWidget(viewer, stretch=1)
body.addWidget(summary, stretch=2)
layout.addLayout(body)

layout.addWidget(QLabel("Read-only side-by-side dictionary display"))
viewer.search_edit.setText("score")

widget.resize(900, 700)
widget.show()

app.exec_()
