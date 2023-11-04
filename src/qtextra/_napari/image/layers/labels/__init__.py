import napari.layers.labels.labels
from napari.layers.labels.labels import Labels

from qtextra._napari.image.layers.labels import _labels_key_bindings
from qtextra._napari.image.layers.labels._labels_mouse_bindings import draw

# Note that importing _labels_key_bindings is needed as the Labels layer gets
# decorated with keybindings during that process, but it is not directly needed
# by our users and so is deleted below
del _labels_key_bindings


# monkeypatch this function to enable left-click draw and right-click erase
napari.layers.labels.labels.draw = draw


__all__ = ["Labels"]
