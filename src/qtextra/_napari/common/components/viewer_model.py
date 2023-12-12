"""Base viewer."""
import typing as ty
import warnings

import napari.layers as n_layers
import numpy as np
from napari.components.cursor import Cursor
from napari.components.dims import Dims
from napari.components.grid import GridCanvas
from napari.components.overlays import Overlay
from napari.components.tooltip import Tooltip
from napari.settings import get_settings
from napari.utils._register import create_func as create_add_method
from napari.utils.events import Event, EventedDict, EventedModel, disconnect_events
from napari.utils.key_bindings import KeymapProvider
from napari.utils.mouse_bindings import MousemapProvider
from napari.utils.theme import available_themes, is_theme_available
from pydantic import Extra, Field, PrivateAttr, validator

from qtextra._napari.common.components.layerlist import LayerList

try:
    from napari_plot.components.gridlines import GridLines
except ImportError:
    GridLines = None


def _current_theme():
    return get_settings().appearance.theme


DEFAULT_OVERLAYS = {}
if GridLines:
    DEFAULT_OVERLAYS["grid_lines"] = GridLines


class ViewerModelBase(KeymapProvider, MousemapProvider, EventedModel):
    """Viewer containing the rendered scene, layers and controlling elements."""

    # Using allow_mutation=False means these attributes aren't settable and don't
    # have an event emitter associated with them
    grid: GridCanvas = Field(default_factory=GridCanvas, allow_mutation=False)
    dims: Dims = Field(default_factory=Dims, allow_mutation=False)
    cursor: Cursor = Field(default_factory=Cursor, allow_mutation=False)
    layers: LayerList = Field(default_factory=LayerList, allow_mutation=False)

    # private track of overlays, only expose the old ones for backward compatibility
    _overlays: EventedDict[str, Overlay] = PrivateAttr(default_factory=EventedDict)

    help: str = ""
    status: ty.Union[str, ty.Dict] = "Ready"
    title: str = "qtextra"
    tooltip: Tooltip = Field(default_factory=Tooltip, allow_mutation=False)
    theme: str = Field(default_factory=_current_theme)

    # 2-tuple indicating height and width
    _canvas_size: ty.Tuple[int, int] = (400, 400)
    # To check if mouse is over canvas to avoid race conditions between
    # different events systems
    mouse_over_canvas: bool = False

    def __init__(
        self,
        title: str = "qtextra",
        ndisplay: int = 2,
        order: ty.Tuple[int, ...] = (),
        axis_labels: ty.Tuple[str, ...] = (),
    ):
        self.__config__.extra = Extra.allow
        super().__init__(
            title=title,
            dims={
                "axis_labels": axis_labels,
                "ndisplay": ndisplay,
                "order": order,
            },
        )
        self.__config__.extra = Extra.ignore

        # Add extra events - ideally these will be removed too!
        self.events.add(layers_change=Event, reset_view=Event, clear_canvas=Event)

        # Connect events
        self.grid.events.connect(self.reset_view)
        self.grid.events.connect(self._on_grid_change)

        self.dims.events.ndisplay.connect(self._update_layers)
        self.dims.events.ndisplay.connect(self.reset_view)
        self.dims.events.order.connect(self._update_layers)
        self.dims.events.order.connect(self.reset_view)
        self.dims.events.current_step.connect(self._update_layers)

        self.cursor.events.position.connect(self._update_status_bar_from_cursor)

        self.layers.events.inserted.connect(self._on_add_layer)
        self.layers.events.removed.connect(self._on_remove_layer)
        self.layers.events.reordered.connect(self._on_grid_change)
        self.layers.events.reordered.connect(self._on_layers_change)
        self.layers.selection.events.active.connect(self._on_active_layer)

        self._overlays.update({k: v() for k, v in DEFAULT_OVERLAYS.items()})

    def _tooltip_visible_update(self, event):
        self.tooltip.visible = event.value

    @property
    def grid_lines(self) -> "GridLines":
        return self._overlays["grid_lines"]

    def __hash__(self):
        return id(self)

    def __str__(self):
        """Simple string representation."""
        return f"qtextra.Viewer: {self.title}"

    def _update_viewer_grid(self):
        """Keep viewer grid settings up to date with settings values."""
        # settings = get_settings()
        #
        # self.grid.stride = settings.application.grid_stride
        # self.grid.shape = (
        #     settings.application.grid_height,
        #     settings.application.grid_width,
        # )

    @validator("theme", allow_reuse=True)
    def _valid_theme(cls, v):
        if not is_theme_available(v):
            themes = ", ".join(available_themes())
            raise ValueError(f"Theme '{v}' not found; options are {themes}.")
        return v

    def clear_canvas(self) -> None:
        """Remove all layers from the canvas."""
        self.layers.remove_all()
        self.events.clear_canvas()

    def reset_view(self, _event=None) -> None:
        """Reset the camera view."""
        extent = self._sliced_extent_world
        scene_size = extent[1] - extent[0]
        corner = extent[0]
        grid_size = list(self.grid.actual_shape(len(self.layers)))
        if len(scene_size) > len(grid_size):
            grid_size = [1] * (len(scene_size) - len(grid_size)) + grid_size
        size = np.multiply(scene_size, grid_size)
        center = np.add(corner, np.divide(size, 2))[-self.dims.ndisplay :]
        center = [0] * (self.dims.ndisplay - len(center)) + list(center)
        self.camera.center = center
        # zoom is defined as the number of canvas pixels per world pixel
        # The default value used below will zoom such that the whole field
        # of view will occupy 95% of the canvas on the most filled axis
        if np.max(size) == 0:
            self.camera.zoom = 0.99 * np.min(self._canvas_size)
        else:
            self.camera.zoom = 0.99 * np.min(np.array(self._canvas_size) / np.array(size[-2:]))
            # self.camera.zoom = 0.99 * np.min(self._canvas_size) / np.max(size[-2:])
        self.camera.angles = (0, 0, 90)

        # Emit a reset view event, which is no longer used internally, but
        # which maybe useful for building on napari.
        self.events.reset_view(
            center=self.camera.center,
            zoom=self.camera.zoom,
            angles=self.camera.angles,
        )

    @property
    def _sliced_extent_world(self) -> np.ndarray:
        """Extent of layers in world coordinates after slicing.

        D is either 2 or 3 depending on if the displayed data is 2D or 3D.

        Returns
        -------
        sliced_extent_world : array, shape (2, D)
        """
        if len(self.layers) == 0 and self.dims.ndim != 2:
            # If no data is present and dims model has not been reset to 0
            # than someone has passed more than two axis labels which are
            # being saved and so default values are used.
            return np.vstack([np.zeros(self.dims.ndim), np.repeat(512, self.dims.ndim)])
        return self.layers.extent.world[:, self.dims.displayed]

    def _on_grid_change(self, event) -> None:
        """Arrange the current layers is a 2D grid."""
        extent = self._sliced_extent_world
        n = len(self.layers)
        for i, layer in enumerate(self.layers):
            i_row, i_column = self.grid.position(n - 1 - i, n)
            self._subplot(layer, (i_row, i_column), extent)

    def _subplot(self, layer, position, extent):
        """Shift a layer to a specified position in a 2D grid.

        Parameters
        ----------
        layer : napari.layers.Layer
            Layer that is to be moved.
        position : 2-tuple of int
            New position of layer in grid.
        extent : array, shape (2, D)
            Extent of the world.
        """
        scene_shift = extent[1] - extent[0] + 1
        translate_2d = np.multiply(scene_shift[-2:], position)
        translate = [0] * layer.ndim
        translate[-2:] = translate_2d
        layer._translate_grid = translate

    def _update_layers(self, event=None, layers=None):
        """Updates the contained layers.

        Parameters
        ----------
        event :
            Event
        layers : list of napari.layers.Layer, optional
            List of layers to update. If none provided updates all.
        """
        layers = layers or self.layers
        for layer in layers:
            layer._slice_dims(self.dims.point, self.dims.ndisplay, self.dims.order)

    def _on_add_layer(self, event):
        """Connect new layer events.

        Parameters
        ----------
        event : :class:`napari.layers.Layer`
            Layer to add.
        """
        layer = event.value

        # Connect individual layer events to viewer events
        # TODO: in a future PR, we should now be able to connect viewer *only*
        # to viewer.layers.events... and avoid direct viewer->layer connections
        layer.events.mouse_pan.connect(self._update_mouse_pan)
        layer.events.mouse_zoom.connect(self._update_mouse_zoom)
        layer.events.cursor.connect(self._update_cursor)
        layer.events.cursor_size.connect(self._update_cursor_size)
        layer.events.data.connect(self._on_layers_change)
        layer.events.scale.connect(self._on_layers_change)
        layer.events.translate.connect(self._on_layers_change)
        layer.events.rotate.connect(self._on_layers_change)
        layer.events.shear.connect(self._on_layers_change)
        layer.events.affine.connect(self._on_layers_change)
        layer.events.name.connect(self.layers._update_name)

        # Update dims and grid model
        self._on_layers_change(None)
        self._on_grid_change(None)
        # Slice current layer based on dims
        self._update_layers(layers=[layer])

        if len(self.layers) == 1:
            self.reset_view()

    def _on_layers_change(self, event):
        if len(self.layers) == 0:
            self.dims.ndim = 2
            self.dims.reset()
        else:
            extent = self.layers.extent
            world = extent.world
            ss = extent.step
            ndim = world.shape[1]
            self.dims.ndim = ndim
            for i in range(ndim):
                self.dims.set_range(i, (world[0, i], world[1, i], ss[i]))
        self.cursor.position = (0,) * self.dims.ndim
        self.events.layers_change()

    def _on_remove_layer(self, event):
        """Disconnect old layer events.

        Parameters
        ----------
        event : napari.utils.event.Event
            Event which will remove a layer.

        Returns
        -------
        layer : :class:`napari.layers.Layer` or list
            The layer that was added (same as input).
        """
        layer = event.value

        # Disconnect all connections from layer
        disconnect_events(layer.events, self)
        disconnect_events(layer.events, self.layers)

        self._on_layers_change(None)
        self._on_grid_change(None)

    def add_layer(self, layer: n_layers.Layer) -> n_layers.Layer:
        """Add a layer to the viewer.

        Parameters
        ----------
        layer : :class:`napari.layers.Layer`
            Layer to add.

        Returns
        -------
        layer : :class:`napari.layers.Layer` or list
            The layer that was added (same as input).
        """
        # Adding additional functionality inside `add_layer`
        # should be avoided to keep full functionality
        # from adding a layer through the `layers.append`
        # method
        self.layers.append(layer)
        return layer

    def _on_active_layer(self, event):
        """Update viewer state for a new active layer."""
        active_layer = event.value
        if active_layer is None:
            self.help = ""
            self.cursor.style = "standard"
        else:
            self.help = active_layer.help
            self.cursor.style = active_layer.cursor
            self.cursor.size = active_layer.cursor_size
            self.camera.mouse_pan = active_layer.mouse_pan
            self.camera.mouse_zoom = active_layer.mouse_zoom
            self._update_status_bar_from_cursor()

    def _update_status_bar_from_cursor(self, event: Event = None) -> None:
        """Update the status bar based on the current cursor position.

        This is generally used as a callback when cursor.position is updated.
        """
        # Update status and help bar based on active layer
        if not self.mouse_over_canvas:
            self.status = ""
            return
        active = self.layers.selection.active
        if active is not None:
            self.status = active.get_status(
                self.cursor.position,
                view_direction=self.cursor._view_direction,
                dims_displayed=list(self.dims.displayed),
                world=True,
            )

            self.help = active.help
            if self.tooltip.visible:
                self.tooltip.text = active._get_tooltip_text(
                    self.cursor.position,
                    view_direction=self.cursor._view_direction,
                    dims_displayed=list(self.dims.displayed),
                    world=True,
                )
        else:
            self.status = "Ready"

    def _update_mouse_pan(self, event):
        """Set the viewer interactive mouse panning."""
        if event.source is self.layers.selection.active:
            self.camera.mouse_pan = event.mouse_pan

    def _update_mouse_zoom(self, event):
        """Set the viewer interactive mouse zoom."""
        if event.source is self.layers.selection.active:
            self.camera.mouse_zoom = event.mouse_zoom

    def _update_cursor(self, event):
        """Set the viewer cursor with the `event.cursor` string."""
        self.cursor.style = event.cursor

    def _update_cursor_size(self, event):
        """Set the viewer cursor_size with the `event.cursor_size` int."""
        self.cursor.size = event.cursor_size

    def _on_cursor_position_change(self, event):
        """Set the layer cursor position."""
        with warnings.catch_warnings():
            # Catch the deprecation warning on layer.position
            warnings.filterwarnings("ignore", message="layer.position is deprecated")
            for layer in self.layers:
                layer.position = self.cursor.position

        # Update status and help bar based on active layer
        active = self.layers.selection.active
        if active is not None:
            self.status = active.get_status(
                self.cursor.position,
                view_direction=self.cursor._view_direction,
                dims_displayed=list(self.dims.displayed),
                world=True,
            )
            self.help = active.help


for _layer in (n_layers.Image, n_layers.Labels):
    func = create_add_method(_layer)
    setattr(ViewerModelBase, func.__name__, func)
