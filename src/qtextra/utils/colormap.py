"""Colormap."""
import typing as ty

import numpy as np
from vispy.color import Colormap as VispyColormap


def vispy_colormaps(colors: ty.List[np.ndarray]) -> ty.List[VispyColormap]:
    """Return list of colormaps."""
    return [VispyColormap([np.asarray([0.0, 0.0, 0.0, 1.0]), color]) for color in colors]


def vispy_colormap(color, name: str = "") -> VispyColormap:
    """Return vispy colormap."""
    return VispyColormap([np.asarray([0.0, 0.0, 0.0, 1.0]), color])


def napari_colormap(color, name: str = ""):
    """Return napari colormap."""
    from napari.utils.colormaps.colormap_utils import convert_vispy_colormap

    return convert_vispy_colormap(vispy_colormap(color), name=name)
