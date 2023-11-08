"""Container class."""
try:
    from napari_plot._qt.layer_controls.qt_infline_controls import QtInfLineControls
    from napari_plot._qt.layer_controls.qt_line_controls import QtLineControls
    from napari_plot._qt.layer_controls.qt_multiline_controls import QtMultiLineControls
    from napari_plot._qt.layer_controls.qt_region_controls import QtRegionControls
    from napari_plot._qt.layer_controls.qt_scatter_controls import QtScatterControls
    from napari_plot.layers import Centroids, InfLine, Line, MultiLine, Region, Scatter
except ImportError:
    Centroids, InfLine, Line, MultiLine, Region, Scatter = None, None, None, None, None, None
    QtInfLineControls, QtLineControls, QtMultiLineControls, QtRegionControls, QtScatterControls = (
        None,
        None,
        None,
        None,
        None,
    )

# from napari._qt.layer_controls.qt_image_controls import QtImageControls
from napari._qt.layer_controls.qt_surface_controls import QtSurfaceControls
from napari._qt.layer_controls.qt_vectors_controls import QtVectorsControls
from napari.layers import Image, Labels, Points, Shapes, Surface, Vectors
from qtpy.QtWidgets import QFrame, QStackedWidget

from qtextra._napari.common.layer_controls.qt_image_controls import QtImageControls
from qtextra._napari.common.layer_controls.qt_labels_controls import QtLabelsControls
from qtextra._napari.common.layer_controls.qt_points_controls import QtPointsControls
from qtextra._napari.common.layer_controls.qt_shapes_controls import QtShapesControls

layer_to_controls = {
    Labels: QtLabelsControls,
    Image: QtImageControls,  # must be after Labels layer
    Shapes: QtShapesControls,
    Points: QtPointsControls,
    Surface: QtSurfaceControls,
    Vectors: QtVectorsControls,
}
# add if napari-plot is available
if Centroids is not None:
    layer_to_controls.update(
        {
            Line: QtLineControls,
            Centroids: QtLineControls,
            Scatter: QtScatterControls,
            Region: QtRegionControls,
            InfLine: QtInfLineControls,
            MultiLine: QtMultiLineControls,
        }
    )


def create_qt_layer_controls(layer):
    """
    Create a qt controls widget for a layer based on its layer type.

    Parameters
    ----------
    layer : napari.layers._base_layer.Layer
        Layer that needs its controls widget created.

    Returns
    -------
    controls : napari.layers.base.QtLayerControls
        Qt controls widget
    """
    for layer_type, controls in layer_to_controls.items():
        if isinstance(layer, layer_type):
            return controls(layer)

    raise TypeError(f"Could not find QtControls for layer of type {type(layer)}")


class QtLayerControlsContainer(QStackedWidget):
    """Container widget for QtLayerControl widgets.

    Parameters
    ----------
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    empty_widget : qtpy.QtWidgets.QFrame
        Empty placeholder frame for when no layer is selected.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    widgets : dict
        Dictionary of key value pairs matching layer with its widget controls.
        widgets[layer] = controls
    """

    def __init__(self, viewer):
        super().__init__()
        self.setProperty("emphasized", True)
        self.viewer = viewer

        self.setMouseTracking(True)
        self.empty_widget = QFrame()
        self.empty_widget.setObjectName("empty_controls_widget")
        self.widgets = {}
        self.addWidget(self.empty_widget)
        self.setCurrentWidget(self.empty_widget)

        self.viewer.layers.events.inserted.connect(self._add)
        self.viewer.layers.events.removed.connect(self._remove)
        self.viewer.layers.selection.events.active.connect(self._display)
        viewer.dims.events.ndisplay.connect(self._on_ndisplay_changed)

    def _on_ndisplay_changed(self, event):
        """Responds to a change in the dimensionality displayed in the canvas.

        Parameters
        ----------
        event : Event
            Event with the new dimensionality value at `event.value`.
        """
        for widget in self.widgets.values():
            if widget is not self.empty_widget:
                widget.ndisplay = event.value

    def _display(self, event):
        """Change the displayed controls to be those of the target layer.

        Parameters
        ----------
        event : Event
            Event with the target layer at `event.item`.
        """
        layer = event.value
        if layer is None:
            self.setCurrentWidget(self.empty_widget)
        else:
            controls = self.widgets[layer]
            self.setCurrentWidget(controls)

    def _add(self, event):
        """Add the controls target layer to the list of control widgets.

        Parameters
        ----------
        event : Event
            Event with the target layer at `event.value`.
        """
        layer = event.value
        controls = create_qt_layer_controls(layer)
        controls.ndisplay = self.viewer.dims.ndisplay
        self.addWidget(controls)
        self.widgets[layer] = controls

    def _remove(self, event):
        """Remove the controls target layer from the list of control widgets.

        Parameters
        ----------
        event : Event
            Event with the target layer at `event.value`.
        """
        layer = event.value
        controls = self.widgets[layer]
        self.removeWidget(controls)
        controls.close()
        controls = None
        del self.widgets[layer]
