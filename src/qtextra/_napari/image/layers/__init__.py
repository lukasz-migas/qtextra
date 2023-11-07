"""Layers are the viewable objects that can be added to a viewer.

Custom layers must inherit from Layer and pass along the
`visual node <http://vispy.org/scene.html#module-vispy.scene.visuals>`_
to the super constructor.
"""
from inspect import isabstract

from napari.layers.base import Layer
from napari.utils.misc import all_subclasses

# from qtextra._napari.common.layers.points import Points
# from qtextra._napari.common.layers.shapes import Shapes
# from qtextra._napari.image.layers.labels import Labels

# isabstact check is to exclude _ImageBase class
NAMES = {subclass.__name__.lower() for subclass in all_subclasses(Layer) if not isabstract(subclass)}
del all_subclasses


__all__ = [
    "NAMES",
    "Layer",
    # "Points",
    # "Shapes",
    # "Labels",
]
