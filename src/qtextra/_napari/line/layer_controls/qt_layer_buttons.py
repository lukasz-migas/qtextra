"""Layer buttons."""

import typing as ty

from qtpy.QtWidgets import QFrame, QHBoxLayout

import qtextra.helpers as hp
from qtextra.widgets.qt_button_icon import QtImagePushButton


def make_qta_btn(parent, icon_name: str, tooltip: str, **kwargs: ty.Any) -> QtImagePushButton:
    """Make a button with an icon from QtAwesome."""
    btn = hp.make_qta_btn(parent=parent, icon_name=icon_name, tooltip=tooltip, **kwargs)
    btn.set_normal()
    btn.setProperty("layer_button", True)
    return btn


class QtLayerButtons(QFrame):
    """Button controls for napari layers.

    Parameters
    ----------
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    delete_btn : QtDeleteButton
        Button to delete selected layers.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

        self.delete_btn = make_qta_btn(
            self, "delete", tooltip="Delete selected layers", func=self.viewer.layers.remove_selected
        )
        self.delete_btn.setParent(self)

        self.new_points_btn = make_qta_btn(
            self,
            "new_points",
            "Add new points layer",
            func=lambda: self.viewer.add_points(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_shapes_btn = make_qta_btn(
            self,
            "new_shapes",
            "Add new shapes layer",
            func=lambda: self.viewer.add_shapes(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_v_infline_btn = make_qta_btn(
            self,
            "new_inf_line",
            "Add new vertical infinite line layer",
            func=lambda: self.viewer.add_inf_line(
                [0],
                scale=self.viewer.layers.extent.step,
                orientation="vertical",
            ),
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_points_btn)
        layout.addWidget(self.new_v_infline_btn)
        layout.addStretch(0)
        layout.addWidget(self.delete_btn)
        self.setLayout(layout)


class QtViewerButtons(QFrame):
    """Button controls for the napari viewer.

    Parameters
    ----------
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    parent : QWidget
        parent of the widget

    Attributes
    ----------
    resetViewButton : QtViewerPushButton
        Button resetting the view of the rendered scene.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, viewer, parent=None):
        super().__init__()

        self.viewer = viewer

        self.resetViewButton = make_qta_btn(
            self,
            "home",
            "Reset view",
            func=lambda: self.viewer.reset_view(),
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self.resetViewButton)
        layout.addStretch(0)
        self.setLayout(layout)
