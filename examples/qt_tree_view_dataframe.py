"""Interactive example of grouping and exploring a DataFrame as a tree."""

from __future__ import annotations

import pandas as pd
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QLabel, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_tree_view_dataframe import QtDataFrameTreeWidget


def main() -> None:
    """Show a grouped DataFrame and controls for exploring it."""
    app = QApplication.instance() or QApplication([])
    root = QWidget()
    root.setWindowTitle("DataFrame tree")
    THEMES.apply(root)
    layout = hp.make_h_layout(parent=root)

    frame = pd.DataFrame(
        {
            "compound": ["PC 32:0", "PC 32:0", "PC 32:0", "SM 34:1", "SM 34:1", "TG 50:1"],
            "adduct": ["[M+H]+", "[M+H]+", "[M+Na]+", "[M+H]+", "[M+Na]+", "[M+H]+"],
            "dataset": ["liver", "kidney", "brain", "liver", "brain", "kidney"],
            "ppm": [1.0, -2.0, 3.0, -0.5, 2.0, 4.0],
        }
    )
    tree = QtDataFrameTreeWidget(
        root,
        frame,
        group_by=["compound", "adduct"],
        label_column="dataset",
        aggregations={"ppm": "mean"},
        auto_expand=10,
    )
    layout.addWidget(tree, 1)

    controls = QWidget(root)
    panel = hp.make_v_layout(parent=controls)
    panel.addWidget(QLabel("Group rows"))
    panel.addWidget(
        hp.make_btn(controls, "Compound and adduct", func=lambda: tree.set_group_by(["compound", "adduct"]))
    )
    panel.addWidget(hp.make_btn(controls, "Compound only", func=lambda: tree.set_group_by("compound")))
    panel.addWidget(hp.make_btn(controls, "Flat list", func=lambda: tree.set_group_by(None)))
    panel.addWidget(QLabel("Explore"))
    panel.addWidget(hp.make_btn(controls, "Filter ppm <= 1", func=lambda: tree.set_numeric_filter("ppm", maximum=1)))
    panel.addWidget(hp.make_btn(controls, "Clear filters", func=tree.clear_filters))
    panel.addWidget(
        hp.make_btn(controls, "Sort ppm descending", func=lambda: tree.set_sort("ppm", Qt.SortOrder.DescendingOrder))
    )
    panel.addWidget(hp.make_btn(controls, "Clear sorting", func=tree.clear_sorting))
    panel.addWidget(hp.make_btn(controls, "Color ppm", func=lambda: tree.color_numeric("ppm", vcenter=0)))
    panel.addWidget(hp.make_btn(controls, "Clear colors", func=tree.clear_colors))
    panel.addStretch()
    panel.addWidget(QLabel("Click a header to sort.\nRight-click it for more options."))
    layout.addWidget(controls)
    root.resize(1000, 500)
    root.show()
    app.exec_()


if __name__ == "__main__":
    main()
