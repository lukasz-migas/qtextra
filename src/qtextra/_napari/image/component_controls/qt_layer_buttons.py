"""Layer buttons."""
from napari._qt.dialogs.qt_modal import QtPopup
from napari._qt.widgets.qt_dims_sorter import QtDimsSorter
from napari._qt.widgets.qt_spinbox import QtSpinBox
from napari._qt.widgets.qt_tooltip import QtToolTipLabel
from napari._qt.widgets.qt_viewer_buttons import QtViewerPushButton
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout

import qtextra.helpers as hp
from qtextra._napari.image.components._viewer_key_bindings import toggle_grid, toggle_ndisplay


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
    new_labels_btn : QtViewerPushButton
        Button to add new Label layer.
    new_shapes_btn : QtViewerPushButton
        Button to add new Shapes layer.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.delete_btn = QtQtaViewerPushButton(
            "delete", tooltip="Delete selected layers", slot=self.viewer.layers.remove_selected
        )
        self.delete_btn.setParent(self)

        self.new_points_btn = QtViewerPushButton(
            "new_points",
            "Add new points layer",
            lambda: self.viewer.add_points(
                ndim=max(self.viewer.dims.ndim, 2),
                scale=self.viewer.layers.extent.step,
            ),
        )

        self.new_shapes_btn = QtViewerPushButton(
            "new_shapes",
            "Add new shapes layer",
            lambda: self.viewer.add_shapes(
                ndim=max(self.viewer.dims.ndim, 2),
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_shapes_btn.setParent(self)

        self.new_labels_btn = QtViewerPushButton(
            "new_labels",
            "Add new free-hand draw shapes layer",
            lambda: self.viewer._new_labels(name="Free-draw"),
        )
        self.new_shapes_btn.setParent(self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_points_btn)
        layout.addWidget(self.new_labels_btn)
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
    rollDimsButton : QtViewerPushButton
        Button to roll orientation of spatial dimensions in the napari viewer.
    transposeDimsButton : QtViewerPushButton
        Button to transpose dimensions in the napari viewer.
    resetViewButton : QtViewerPushButton
        Button resetting the view of the rendered scene.
    gridViewButton : QtStateButton
        Button to toggle grid view mode of layers on and off.
    ndisplayButton : QtStateButton
        Button to toggle number of displayed dimensions.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, viewer, parent=None):
        super().__init__()
        self.viewer = viewer

        ndb = QtViewerPushButton("ndisplay_button")
        self.ndisplayButton = ndb
        self.ndisplayButton.setToolTip("Toggle number of displayed dimensions (Ctrl-Y)")
        ndb.setCheckable(True)
        ndb.setChecked(self.viewer.dims.ndisplay == 2)
        ndb.clicked.connect(lambda _: toggle_ndisplay(self.viewer))
        ndb.setContextMenuPolicy(Qt.CustomContextMenu)
        ndb.customContextMenuRequested.connect(self.open_perspective_popup)

        @self.viewer.dims.events.ndisplay.connect
        def _set_ndisplay_mode_checkstate(event):
            ndb.setChecked(event.value == 2)

        self.rollDimsButton = QtViewerPushButton(
            "roll",
            "Roll dimensions order for display (Ctrl-E)",
            lambda: self.viewer.dims._roll(),
        )
        self.rollDimsButton.setContextMenuPolicy(Qt.CustomContextMenu)
        self.rollDimsButton.customContextMenuRequested.connect(self.open_roll_popup)

        self.transposeDimsButton = QtViewerPushButton(
            "transpose",
            "Transpose displayed dimensions (Ctrl-T)",
            lambda: self.viewer.dims._transpose(),
        )

        gvb = QtViewerPushButton("grid_view_button")
        self.gridViewButton = gvb
        gvb.setCheckable(True)
        gvb.setChecked(viewer.grid.enabled)
        gvb.setContextMenuPolicy(Qt.CustomContextMenu)
        gvb.clicked.connect(lambda _: toggle_grid(self.viewer))
        gvb.customContextMenuRequested.connect(self.open_grid_popup)
        self.gridViewButton.setToolTip("Toggle grid view (Ctrl-G)")

        @self.viewer.grid.events.enabled.connect
        def _set_grid_mode_checkstate(event):
            gvb.setChecked(event.value)

        self.resetViewButton = QtViewerPushButton(
            "home",
            "Reset view (Ctrl-R)",
            lambda: self.viewer.reset_view(),
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
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
        sld = QSlider(Qt.Horizontal, self)
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
        # widgets
        popup = QtPopup(self)
        grid_stride = QtSpinBox(popup)
        grid_width = QtSpinBox(popup)
        grid_height = QtSpinBox(popup)
        shape_help_symbol = QtToolTipLabel(self)
        stride_help_symbol = QtToolTipLabel(self)
        blank = QLabel(self)  # helps with placing help symbols.

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
        stride_min = self.viewer.grid.__fields__["stride"].type_.ge
        stride_max = self.viewer.grid.__fields__["stride"].type_.le
        stride_not = self.viewer.grid.__fields__["stride"].type_.ne
        grid_stride.setObjectName("gridStrideBox")
        grid_stride.setAlignment(Qt.AlignCenter)
        grid_stride.setRange(stride_min, stride_max)
        grid_stride.setProhibitValue(stride_not)
        grid_stride.setValue(self.viewer.grid.stride)
        grid_stride.valueChanged.connect(self._update_grid_stride)

        width_min = self.viewer.grid.__fields__["shape"].sub_fields[1].type_.ge
        width_not = self.viewer.grid.__fields__["shape"].sub_fields[1].type_.ne
        grid_width.setObjectName("gridWidthBox")
        grid_width.setAlignment(Qt.AlignCenter)
        grid_width.setMinimum(width_min)
        grid_width.setProhibitValue(width_not)
        grid_width.setValue(self.viewer.grid.shape[1])
        grid_width.valueChanged.connect(self._update_grid_width)

        height_min = self.viewer.grid.__fields__["shape"].sub_fields[0].type_.ge
        height_not = self.viewer.grid.__fields__["shape"].sub_fields[0].type_.ne
        grid_height.setObjectName("gridStrideBox")
        grid_height.setAlignment(Qt.AlignCenter)
        grid_height.setMinimum(height_min)
        grid_height.setProhibitValue(height_not)
        grid_height.setValue(self.viewer.grid.shape[0])
        grid_height.valueChanged.connect(self._update_grid_height)

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

    def _update_grid_width(self, value):
        """Update the width value in grid shape.

        Parameters
        ----------
        value : int
            New grid width value.
        """
        self.viewer.grid.shape = (self.viewer.grid.shape[0], value)

    def _update_grid_stride(self, value):
        """Update stride in grid settings.

        Parameters
        ----------
        value : int
            New grid stride value.
        """
        self.viewer.grid.stride = value

    def _update_grid_height(self, value):
        """Update height value in grid shape.

        Parameters
        ----------
        value : int
            New grid height value.
        """
        self.viewer.grid.shape = (value, self.viewer.grid.shape[1])
