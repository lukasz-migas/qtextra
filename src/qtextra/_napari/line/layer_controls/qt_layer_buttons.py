"""Layer buttons."""
from napari._qt.widgets.qt_viewer_buttons import QtDeleteButton, QtViewerPushButton
from qtpy.QtWidgets import QFrame, QHBoxLayout


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
        self.delete_btn = QtDeleteButton(self.viewer)
        self.delete_btn.setParent(self)

        self.new_points_btn = QtViewerPushButton(
            "new_points",
            "Add new points layer",
            lambda: self.viewer.add_points(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_points_btn.setParent(self)

        self.new_shapes_btn = QtViewerPushButton(
            "new_shapes",
            "Add new shapes layer",
            lambda: self.viewer.add_shapes(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_shapes_btn.setParent(self)

        self.new_v_infline_btn = QtViewerPushButton(
            "new_inf_line",
            "Add new vertical infinite line layer",
            lambda: self.viewer.add_inf_line(
                [0],
                scale=self.viewer.layers.extent.step,
                orientation="vertical",
            ),
        )
        self.new_v_infline_btn.setParent(self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
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

        self.resetViewButton = QtViewerPushButton(
            "home",
            "Reset view (Ctrl-R)",
            lambda: self.viewer.reset_view(),
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.resetViewButton)
        layout.addStretch(0)
        self.setLayout(layout)
