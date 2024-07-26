"""Extents."""

import numpy as np


class Extents:
    """Simple class that handles plotting extents."""

    def __init__(self):
        self.x = []
        self.y = []

    def reset(self):
        """Clear extents."""
        self.x.clear()
        self.y.clear()

    def add_range(self, xmin, xmax, ymin, ymax):
        """Add new values."""
        self.x.extend([xmin, xmax])
        self.y.extend([ymin, ymax])

    def get_x(self):
        """Get x_min, x_max."""
        return np.nanmin(self.x), np.nanmax(self.x)

    def get_y(self):
        """Get y_min, y_max."""
        return np.nanmin(self.y), np.nanmax(self.y)

    def get_xy(self):
        return np.nanmin(self.x), np.nanmax(self.x), np.nanmin(self.y), np.nanmax(self.y)
