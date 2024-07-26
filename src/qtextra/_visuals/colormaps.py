"""Colormap utilities."""

# Third-party imports
import numpy as np
from matplotlib import cm


def set_colormap(cmap="viridis", img_view=None):
    # Get the colormap
    colormap = cm.get_cmap(cmap)
    colormap._init()
    lut = (colormap._lut * 255).view(np.ndarray)  # Convert matplotlib colormap from 0-1 to 0 -255 for Qt

    # Apply the colormap
    if img_view is None:
        return lut

    img_view.setLookupTable(lut)
