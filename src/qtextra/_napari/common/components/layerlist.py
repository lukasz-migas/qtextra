from napari.components.layerlist import Extent
from napari.components.layerlist import LayerList as _LayerList


class LayerList(_LayerList):
    """Monkey-patched layer list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def selection_extent(self) -> Extent:
        """Extent of layers in data and world coordinates."""
        extent_list = [layer.extent for layer in self.selection]
        return Extent(
            data=None,
            world=self._get_extent_world(extent_list),
            step=self._get_step_size(extent_list),
        )

    def extent_for(self, layers) -> Extent:
        """Extent of layers in data and world coordinates."""
        extent_list = [layer.extent for layer in layers]
        return Extent(
            data=None,
            world=self._get_extent_world(extent_list),
            step=self._get_step_size(extent_list),
        )

    def toggle_selected_editable(self) -> None:
        """Toggle editable of selected layers."""
        for layer in self:
            if layer in self.selection:
                layer.editable = not layer.editable

    def remove_all(self) -> None:
        """Remove all layers."""
        self.select_all()
        self.remove_selected()
