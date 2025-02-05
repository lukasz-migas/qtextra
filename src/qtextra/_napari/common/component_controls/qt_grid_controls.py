"""Grid controls."""

from __future__ import annotations

from napari._qt.widgets.qt_spinbox import QtSpinBox
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QLabel, QWidget

import qtextra.helpers as hp
from qtextra._napari.image.components.viewer_model import ViewerModel
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtextra.widgets.qt_label_icon import QtQtaTooltipLabel


class QtGridControls(QtFramelessPopup):
    def __init__(self, viewer: ViewerModel, parent: QWidget | None = None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("scalebar")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        # widgets

        shape_help_msg = (
            "Number of rows and columns in the grid. A value of -1 for either or both of width and height will\n"
            " trigger an auto calculation of the necessary grid shape to appropriately fill all the layers at the\n"
            " appropriate stride. 0 is not a valid entry."
        )

        stride_help_msg = (
            "Number of layers to place in each grid square before moving on to the next square. The default ordering\n"
            " is to place the most visible layer in the top left corner of the grid. A negative stride will cause the\n"
            " order in which the layers are placed in the grid to be reversed. 0 is not a valid entry."
        )

        # set up
        stride_min = self.viewer.grid.__fields__["stride"].type_.ge
        stride_max = self.viewer.grid.__fields__["stride"].type_.le
        stride_not = self.viewer.grid.__fields__["stride"].type_.ne
        grid_stride = QtSpinBox(self)
        grid_stride.setObjectName("gridStrideBox")
        grid_stride.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_stride.setRange(stride_min, stride_max)
        grid_stride.setProhibitValue(stride_not)
        grid_stride.setValue(self.viewer.grid.stride)
        grid_stride.valueChanged.connect(self._update_grid_stride)

        width_min = self.viewer.grid.__fields__["shape"].sub_fields[1].type_.ge
        width_not = self.viewer.grid.__fields__["shape"].sub_fields[1].type_.ne
        grid_width = QtSpinBox(self)
        grid_width.setObjectName("gridWidthBox")
        grid_width.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_width.setMinimum(width_min)
        grid_width.setProhibitValue(width_not)
        grid_width.setValue(self.viewer.grid.shape[1])
        grid_width.valueChanged.connect(self._update_grid_width)

        height_min = self.viewer.grid.__fields__["shape"].sub_fields[0].type_.ge
        height_not = self.viewer.grid.__fields__["shape"].sub_fields[0].type_.ne
        grid_height = QtSpinBox(self)
        grid_height.setObjectName("gridStrideBox")
        grid_height.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_height.setMinimum(height_min)
        grid_height.setProhibitValue(height_not)
        grid_height.setValue(self.viewer.grid.shape[0])
        grid_height.valueChanged.connect(self._update_grid_height)

        shape_help_symbol_width = QtQtaTooltipLabel(parent=self)
        shape_help_symbol_width.setToolTip(shape_help_msg)

        shape_help_symbol_height = QtQtaTooltipLabel(parent=self)
        shape_help_symbol_height.setToolTip(shape_help_msg)

        stride_help_symbol = QtQtaTooltipLabel(parent=self)
        stride_help_symbol.setToolTip(stride_help_msg)

        # layout
        layout = hp.make_form_layout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.insertRow(0, QLabel("Grid stride:"), hp.make_h_layout(grid_stride, stride_help_symbol, stretch_id=0))
        layout.insertRow(1, QLabel("Grid width:"), hp.make_h_layout(grid_width, shape_help_symbol_width, stretch_id=0))
        layout.insertRow(
            2, QLabel("Grid height:"), hp.make_h_layout(grid_height, shape_help_symbol_height, stretch_id=0)
        )
        return layout

    def _update_grid_width(self, value):
        """Update the width value in grid shape."""
        self.viewer.grid.shape = (self.viewer.grid.shape[0], value)

    def _update_grid_stride(self, value):
        """Update stride in grid settings."""
        self.viewer.grid.stride = value

    def _update_grid_height(self, value):
        """Update height value in grid shape."""
        self.viewer.grid.shape = (value, self.viewer.grid.shape[1])
