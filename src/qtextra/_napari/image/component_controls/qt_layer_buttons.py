"""Layer buttons."""

from __future__ import annotations

import typing as ty

from napari._qt.dialogs.qt_modal import QtPopup
from napari._qt.widgets.qt_dims_sorter import QtDimsSorter
from napari._qt.widgets.qt_spinbox import QtSpinBox
from napari._qt.widgets.qt_tooltip import QtToolTipLabel
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra._napari.image.components._viewer_key_bindings import toggle_grid, toggle_ndisplay
from qtextra.widgets.qt_button_icon import QtImagePushButton

if ty.TYPE_CHECKING:
    from qtextra._napari.image.components.viewer_model import ViewerModel


def make_qta_btn(parent, icon_name: str, tooltip: str, **kwargs: ty.Any) -> QtImagePushButton:
    """Make a button with an icon from QtAwesome."""
    btn = hp.make_qta_btn(parent=parent, icon_name=icon_name, tooltip=tooltip, **kwargs)
    btn.set_normal()
    btn.setProperty("layer_button", True)
    return btn


class QtLayerButtons(QFrame):
    """Button controls for napari layers."""

    def __init__(self, viewer: ViewerModel, disable_new_layers: bool = False, **_kwargs: ty.Any):
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
                ndim=max(self.viewer.dims.ndim, 2),
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_shapes_btn = make_qta_btn(
            self,
            "new_shapes",
            "Add new shapes layer",
            func=lambda: self.viewer.add_shapes(
                ndim=max(self.viewer.dims.ndim, 2),
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_labels_btn = make_qta_btn(
            self,
            "new_labels",
            "Add new free-hand draw shapes layer",
            func=lambda: self.viewer._new_labels(name="Free-draw"),
        )
        if disable_new_layers:
            self.new_points_btn.hide()
            self.new_shapes_btn.hide()
            self.new_labels_btn.hide()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.new_points_btn)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_labels_btn)
        layout.addStretch(0)
        layout.addWidget(self.delete_btn)
        self.setLayout(layout)


class QtViewerButtons(QFrame):
    """Button controls for the napari viewer."""

    def __init__(self, viewer, parent=None):
        super().__init__()
        self.viewer = viewer

        self.ndisplayButton = make_qta_btn(
            self,
            "ndisplay_off",
            "Toggle number of displayed dimensions",
            checkable=True,
            checked=self.viewer.dims.ndisplay == 3,
            checked_icon_name="ndisplay_on",
            func=lambda: toggle_ndisplay(self.viewer),
            func_menu=self.open_perspective_popup,
        )

        self.rollDimsButton = make_qta_btn(
            self,
            "roll",
            "Roll dimensions order for display. Right-click on the button to manually order dimensions.",
            func=lambda: viewer.dims._roll(),
            func_menu=self.open_roll_popup,
        )

        self.transposeDimsButton = make_qta_btn(
            self,
            "transpose",
            "Transpose displayed dimensions.",
            func=lambda: viewer.dims.transpose(),
        )

        self.gridViewButton = make_qta_btn(
            self,
            "grid_off",
            "Toggle grid view. Right-click on the button to change grid settings.",
            checkable=True,
            checked=viewer.grid.enabled,
            checked_icon_name="grid_on",
            func=lambda: toggle_grid(viewer),
            func_menu=self.open_grid_popup,
        )

        @self.viewer.grid.events.enabled.connect
        def _set_grid_mode_checkstate(event):
            self.gridViewButton.setChecked(event.value)

        self.resetViewButton = make_qta_btn(
            self,
            "home",
            "Reset view",
            func=lambda: self.viewer.reset_view(),
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.ndisplayButton)
        layout.addWidget(self.rollDimsButton)
        layout.addWidget(self.transposeDimsButton)
        layout.addWidget(self.gridViewButton)
        layout.addWidget(self.resetViewButton)
        layout.addStretch(0)
        self.setLayout(layout)

    def open_roll_popup(self):
        """Open a grid popup to manually order the dimensions."""
        if self.viewer.dims.ndisplay != 2:
            return

        dim_sorter = QtDimsSorter(self.viewer, self)
        dim_sorter.setObjectName("dim_sorter")

        # make layout
        layout = QHBoxLayout()
        layout.addWidget(dim_sorter)

        # popup and show
        pop = QtPopup(self)
        pop.frame.setLayout(layout)
        pop.show_above_mouse()

    def open_perspective_popup(self):
        """Show a slider to control the viewer `camera.perspective`."""
        if self.viewer.dims.ndisplay != 3:
            return

        # make slider connected to perspective parameter
        sld = QSlider(Qt.Orientation.Horizontal, self)
        sld.setRange(0, max(90, self.viewer.camera.perspective))
        sld.setValue(self.viewer.camera.perspective)
        sld.valueChanged.connect(lambda v: setattr(self.viewer.camera, "perspective", v))

        # make layout
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Perspective"))
        layout.addWidget(sld)

        # popup and show
        pop = QtPopup(self)
        pop.frame.setLayout(layout)
        pop.show_above_mouse()

    def open_grid_popup(self):
        """Open grid options pop up widget."""
        make_grid_popup(self, self.viewer)


def make_grid_popup(parent: QWidget, viewer: ViewerModel) -> None:
    """Make grid popup."""

    def _update_grid_width(value):
        viewer.grid.shape = (viewer.grid.shape[0], value)

    def _update_grid_stride(value):
        viewer.grid.stride = value

    def _update_grid_height(value):
        viewer.grid.shape = (value, viewer.grid.shape[1])

    popup = QtPopup(parent)
    grid_stride = QtSpinBox(popup)
    grid_width = QtSpinBox(popup)
    grid_height = QtSpinBox(popup)
    shape_help_symbol = QtToolTipLabel(parent)
    stride_help_symbol = QtToolTipLabel(parent)
    blank = QLabel(parent)  # helps with placing help symbols.

    shape_help_msg = (
        "Number of rows and columns in the grid. A value of -1 for either or both of width and height will trigger"
        " an auto calculation of the necessary grid shape to appropriately fill all the layers at the appropriate"
        " stride. 0 is not a valid entry."
    )

    stride_help_msg = (
        "Number of layers to place in each grid square before moving on to the next square. The default ordering"
        " is to place the most visible layer in the top left corner of the grid. A negative stride will cause the"
        " order in which the layers are placed in the grid to be reversed. 0 is not a valid entry."
    )

    # set up
    stride_min = viewer.grid.__fields__["stride"].type_.ge
    stride_max = viewer.grid.__fields__["stride"].type_.le
    stride_not = viewer.grid.__fields__["stride"].type_.ne
    grid_stride.setObjectName("gridStrideBox")
    grid_stride.setAlignment(Qt.AlignmentFlag.AlignCenter)
    grid_stride.setRange(stride_min, stride_max)
    grid_stride.setProhibitValue(stride_not)
    grid_stride.setValue(viewer.grid.stride)
    grid_stride.valueChanged.connect(_update_grid_stride)

    width_min = viewer.grid.__fields__["shape"].sub_fields[1].type_.ge
    width_not = viewer.grid.__fields__["shape"].sub_fields[1].type_.ne
    grid_width.setObjectName("gridWidthBox")
    grid_width.setAlignment(Qt.AlignmentFlag.AlignCenter)
    grid_width.setMinimum(width_min)
    grid_width.setProhibitValue(width_not)
    grid_width.setValue(viewer.grid.shape[1])
    grid_width.valueChanged.connect(_update_grid_width)

    height_min = viewer.grid.__fields__["shape"].sub_fields[0].type_.ge
    height_not = viewer.grid.__fields__["shape"].sub_fields[0].type_.ne
    grid_height.setObjectName("gridStrideBox")
    grid_height.setAlignment(Qt.AlignmentFlag.AlignCenter)
    grid_height.setMinimum(height_min)
    grid_height.setProhibitValue(height_not)
    grid_height.setValue(viewer.grid.shape[0])
    grid_height.valueChanged.connect(_update_grid_height)

    shape_help_symbol.setObjectName("help_label")
    shape_help_symbol.setToolTip(shape_help_msg)

    stride_help_symbol.setObjectName("help_label")
    stride_help_symbol.setToolTip(stride_help_msg)

    # layout
    form_layout = hp.make_form_layout()
    form_layout.insertRow(0, QLabel("Grid stride:"), grid_stride)
    form_layout.insertRow(1, QLabel("Grid width:"), grid_width)
    form_layout.insertRow(2, QLabel("Grid height:"), grid_height)

    help_layout = QVBoxLayout()
    help_layout.addWidget(stride_help_symbol)
    help_layout.addWidget(blank)
    help_layout.addWidget(shape_help_symbol)

    layout = QHBoxLayout()
    layout.addLayout(form_layout)
    layout.addLayout(help_layout)

    popup.frame.setLayout(layout)

    popup.show_above_mouse()

    # adjust placement of shape help symbol.  Must be done last
    # in order for this movement to happen.
    delta_x = 0
    delta_y = -15
    shape_pos = (
        shape_help_symbol.x() + delta_x,
        shape_help_symbol.y() + delta_y,
    )
    shape_help_symbol.move(QPoint(*shape_pos))
