"""Viewer model."""

from __future__ import annotations

import typing as ty

import napari.layers as n_layers
import numpy as np
from napari import Viewer as NapariViewer
from napari.components._viewer_mouse_bindings import dims_scroll
from napari.components.camera import Camera
from napari.components.overlays import AxesOverlay, BrushCircleOverlay, ScaleBarOverlay
from napari.components.overlays.text import TextOverlay
from napari.types import PathOrPaths
from napari.utils._register import create_func as create_add_method
from napari.utils.events import Event
from pydantic import Field

from qtextra._napari.common.components.overlays.color_bar import ColorBarOverlay
from qtextra._napari.common.components.overlays.crosshair import CrossHairOverlay
from qtextra._napari.common.components.viewer_model import ViewerModelBase

# from qtextra._napari.image import layers
from qtextra._napari.image.components._viewer_mouse_bindings import crosshair

DEFAULT_OVERLAYS = {
    "scale_bar": ScaleBarOverlay,
    "text": TextOverlay,
    "axes": AxesOverlay,
    "brush_circle": BrushCircleOverlay,
    "cross_hair": CrossHairOverlay,
    "color_bar": ColorBarOverlay,
}


# noinspection PyMissingOrEmptyDocstring
class ViewerModel(ViewerModelBase):
    """Viewer containing the rendered scene, layers, and controlling elements
    including dimension sliders, and control bars for color limits.

    Parameters
    ----------
    title : string
        The title of the viewer window.
    ndisplay : {2, 3}
        Number of displayed dimensions.
    order : tuple of int
        Order in which dimensions are displayed where the last two or last
        three dimensions correspond to row x column or plane x row x column if
        ndisplay is 2 or 3.
    axis_labels : list of str
        Dimension names.
    """

    # Using allow_mutation=False means these attributes aren't settable and don't
    # have an event emitter associated with them
    camera: Camera = Field(default_factory=Camera, allow_mutation=False)

    def __init__(
        self,
        title: str = "qtextra",
        ndisplay: int = 2,
        order: ty.Tuple[int, ...] = (),
        axis_labels: ty.Tuple[str, ...] = (),
        **kwargs: ty.Any,
    ):
        # allow extra attributes during model initialization, useful for mixins
        super().__init__(title=title, ndisplay=ndisplay, order=order, axis_labels=axis_labels)

        self.events.add(crosshair=Event)

        # Add mouse callback
        self.mouse_wheel_callbacks.append(dims_scroll)
        if kwargs.get("allow_crosshair", True):
            self.mouse_drag_callbacks.append(crosshair)

        self._overlays.update({k: v() for k, v in DEFAULT_OVERLAYS.items()})
        NapariViewer._instances.add(self)

    # simple properties exposing overlays for backward compatibility
    @property
    def axes(self) -> AxesOverlay:
        return self._overlays["axes"]

    @property
    def scale_bar(self) -> ScaleBarOverlay:
        return self._overlays["scale_bar"]

    @property
    def text_overlay(self) -> TextOverlay:
        return self._overlays["text"]

    @property
    def cross_hair(self) -> CrossHairOverlay:
        return self._overlays["cross_hair"]

    @property
    def color_bar(self) -> ColorBarOverlay:
        return self._overlays["color_bar"]

    @property
    def _brush_circle_overlay(self) -> BrushCircleOverlay:
        return self._overlays["brush_circle"]

    def _new_labels(self, name: str | None = None) -> n_layers.Labels:
        """Create new labels layer filling full world coordinates space."""
        extent = self.layers.extent.world
        scale = self.layers.extent.step
        scene_size = extent[1] - extent[0]
        corner = extent[0] + 0.5 * scale
        shape = [np.round(s / sc).astype("int") + 1 if s > 0 else 1 for s, sc in zip(scene_size, scale)]
        empty_labels = np.zeros(shape, dtype=int)
        return self.add_labels(empty_labels, name=name, translate=np.array(corner), scale=scale)

    def new_labels_for_image(self, layers, name: str | None = None) -> n_layers.Labels:
        """Create new labels layer filling full world coordinates space."""
        extent = self.layers.extent.world
        scale = self.layers.extent.step
        scene_size = extent[1] - extent[0]
        corner = extent[0] + 0.5 * self.layers.extent.step
        shape = [np.round(s / sc).astype("int") if s > 0 else 1 for s, sc in zip(scene_size, scale)]
        empty_labels = np.zeros(shape, dtype=int)
        return self.add_labels(empty_labels, name=name, translate=np.array(corner), scale=scale)

    def add_image(self, *args, **kwargs) -> n_layers.Image:
        """Add image."""
        return NapariViewer.add_image(self, *args, **kwargs)

    def add_shapes(self, *args, **kwargs) -> n_layers.Shapes:
        """Add image."""
        return NapariViewer.add_shapes(self, *args, **kwargs)

    def add_points(self, *args, **kwargs) -> n_layers.Points:
        """Add image."""
        return NapariViewer.add_points(self, *args, **kwargs)

    def add_labels(self, *args, **kwargs) -> n_layers.Shapes:
        """Add image."""
        return NapariViewer.add_labels(self, *args, **kwargs)

    def open(
        self,
        path: PathOrPaths,
        *,
        stack: bool = False,
        plugin: ty.Optional[str] = None,
        layer_type: ty.Optional[str] = None,
        **kwargs: ty.Any,
    ) -> ty.List[n_layers.Layer]:
        """Open a path or list of paths with plugins, and add layers to viewer.

        A list of paths will be handed one-by-one to the napari_get_reader hook
        if stack is False, otherwise the full list is passed to each plugin
        hook.

        Parameters
        ----------
        path : str or list of str
            A filepath, directory, or URL (or a list of any) to open.
        stack : bool, optional
            If a list of strings is passed and ``stack`` is ``True``, then the
            entire list will be passed to plugins.  It is then up to individual
            plugins to know how to handle a list of paths.  If ``stack`` is
            ``False``, then the ``path`` list is broken up and passed to plugin
            readers one by one.  by default False.
        plugin : str, optional
            Name of a plugin to use.  If provided, will force ``path`` to be
            read with the specified ``plugin``.  If the requested plugin cannot
            read ``path``, an exception will be raised.
        layer_type : str, optional
            If provided, will force data read from ``path`` to be passed to the
            corresponding ``add_<layer_type>`` method (along with any
            additional) ``kwargs`` provided to this function.  This *may*
            result in exceptions if the data returned from the path is not
            compatible with the layer_type.
        **kwargs
            All other keyword arguments will be passed on to the respective
            ``add_layer`` method.

        Returns
        -------
        layers : list
            A list of any layers that were added to the viewer.
        """
        return NapariViewer.open(self, path, stack=stack, plugin=plugin, layer_type=layer_type, **kwargs)

    def _add_layers_with_plugins(
        self,
        paths: ty.List[str],
        *,
        stack: bool,
        kwargs: ty.Optional[dict] = None,
        plugin: ty.Optional[str] = None,
        layer_type: ty.Optional[str] = None,
    ) -> ty.List[n_layers.Layer]:
        """Load a path or a list of paths into the viewer using plugins.

        This function is mostly called from self.open_path, where the ``stack``
        argument determines whether a list of strings is handed to plugins one
        at a time, or en-masse.

        Returns
        -------
        List[Layer]
            A list of any layers that were added to the viewer.
        """
        return NapariViewer._add_layers_with_plugins(
            paths=paths, stack=stack, kwargs=kwargs, plugin=plugin, layer_type=layer_type
        )

    def _add_layer_from_data(
        self,
        data,
        meta: ty.Optional[ty.Dict[str, ty.Any]] = None,
        layer_type: ty.Optional[str] = None,
    ) -> ty.List[n_layers.Layer]:
        """Add arbitrary layer data to the viewer.

        Primarily intended for usage by reader plugin hooks.

        Parameters
        ----------
        data : Any
            Data in a format that is valid for the corresponding `add_*` method
            of the specified ``layer_type``.
        meta : dict, optional
            Dict of keyword arguments that will be passed to the corresponding
            `add_*` method.  MUST NOT contain any keyword arguments that are
            not valid for the corresponding method.
        layer_type : str
            Type of layer to add.  MUST have a corresponding add_* method on
            on the viewer instance.  If not provided, the layer is assumed to
            be "image", unless data.dtype is one of (np.int32, np.uint32,
            np.int64, np.uint64), in which case it is assumed to be "labels".

        Returns
        -------
        layers : list of layers
            A list of layers added to the viewer.

        Raises
        ------
        ValueError
            If ``layer_type`` is not one of the recognized layer types.
        TypeError
            If any keyword arguments in ``meta`` are unexpected for the
            corresponding `add_*` method for this layer_type.

        """
        return NapariViewer._add_layer_from_data(self, data, meta=meta, layer_type=layer_type)


for _layer in (n_layers.Vectors, n_layers.Shapes, n_layers.Points, n_layers.Surface):
    func = create_add_method(_layer)
    setattr(ViewerModel, func.__name__, func)
