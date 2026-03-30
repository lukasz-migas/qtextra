"""QtMultiDictTagEditor."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_multi_dict_tag_editor import QtMultiDictTagEditor

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

layout.addWidget(QLabel("QtMultiDictTagEditor"))
editor = QtMultiDictTagEditor()
editor.set_items(
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
    },
)
layout.addWidget(editor)

layout.addWidget(QLabel("Target one sample or all samples"))
editor.target_combo.setCurrentText("sample_b")
editor.table.selectRow(0)
layout.addStretch()

widget.resize(900, 480)
widget.show()

app.exec_()
