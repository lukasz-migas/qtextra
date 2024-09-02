"""Viewer base."""

import typing as ty
from abc import ABC
from contextlib import suppress

from napari.components.layerlist import LayerList
from napari.layers import Image, Layer


class ViewerBase(ABC):
    """Base class for viewer implementations."""

    IS_VISPY = True
    PLOT_ID = ""
    viewer: ty.Any
    widget: ty.Any
    _callbacks = None

    @property
    def is_vispy(self) -> bool:
        """Flag to say whether this is a vispy-based visualisation."""
        return self.IS_VISPY

    @property
    def figure(self):
        """Canvas."""
        return self.widget.canvas

    @property
    def camera(self):
        """Get camera."""
        return self.widget.view.camera

    def _clear(self, _evt=None) -> None:  # noqa: B027
        """Clear canvas."""

    def clear(self) -> None:
        """Clear canvas."""
        self._clear()
        self.viewer.layers.clear()
        self.viewer.text_overlay.text = ""

    def close(self) -> None:
        """Close the view instance."""
        self.viewer.layers.clear()
        self.widget.close()

    @property
    def layers(self) -> LayerList:
        """Get layer list."""
        return self.viewer.layers

    def get_layer(self, name: str) -> ty.Optional[Layer]:
        """Get layer."""
        try:
            return self.viewer.layers[name]
        except KeyError:
            return None

    def remove_layer(self, name: str, silent: bool = True) -> bool:
        """Remove layer with `name`."""
        try:
            self.viewer.layers.remove(name)
            return True
        except (ValueError, KeyError) as err:
            if not silent:
                print(f"Failed to remove layer `{name}`\n{err}")
        return False

    def remove_layers(self, names: ty.Iterable[str]) -> None:
        """Remove multiple layers."""
        for name in names:
            self.remove_layer(name)

    def try_reuse(self, name: str, cls: ty.Type[Layer]) -> ty.Optional[Layer]:
        """Try retrieving layer from the layer list."""
        try:
            layer = self.viewer.layers[name]
            return layer if isinstance(layer, cls) else None
        except KeyError:
            return None

    def select_one_layer(self, layer: Layer) -> None:
        """Clear current selection and only select one layer."""
        self.viewer.layers.selection.clear()
        self.viewer.layers.selection.add(layer)

    def deselect_one_layer(self, layer: Layer) -> None:
        """Deselect layer."""
        with suppress(KeyError):
            self.viewer.layers.selection.remove(layer)

    def get_layers_of_type(self, cls: Layer) -> ty.List[Layer]:
        """Get all layers of type."""
        layers = []
        for layer in self.viewer.layers:
            if isinstance(layer, cls):
                layers.append(layer)
        return layers

    def get_layers_of_type_with_attr_value(self, cls: Layer, attr: str, value: ty.Any) -> ty.List[Layer]:
        """Get all layers of type."""
        layers = []
        for layer in self.viewer.layers:
            if isinstance(layer, cls):
                if getattr(layer, attr) == value:
                    layers.append(layer)
        return layers

    def update_attribute(self, name: str, **kwargs: ty.Any) -> None:
        """Update attribute."""
        layer = self.get_layer(name)
        if layer:
            for attr, value in kwargs.items():
                if hasattr(layer, attr):
                    try:
                        setattr(layer, attr, value)
                    except Exception as err:
                        print(f"Failed to update attribute: {err}")

    @staticmethod
    def update_image_contrast_limits(image_layer: Image, new_range: ty.Optional[ty.Tuple] = None):
        """Update contrast limits for specified layer."""
        if new_range is None or len(new_range) != 2:
            new_range = image_layer._calc_data_range()
        image_layer.contrast_limits_range = new_range
        image_layer._contrast_limits = tuple(image_layer.contrast_limits_range)
        image_layer.contrast_limits = image_layer._contrast_limits
        image_layer._update_dims()
