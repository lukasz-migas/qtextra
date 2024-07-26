"""Views."""

from typing import Optional

import numpy as np
from koyo.secret import get_short_hash
from qtpy.QtCore import QMutexLocker

from qtextra._visuals.views_base import MUTEX, ViewBase
from qtextra._visuals.vispy.base import PlotLine, PlotScatter


class ViewVispyLine(ViewBase):
    """View."""

    PLOT_TYPE = "line"
    IS_VISPY = True

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.PLOT_ID = get_short_hash()
        self.figure = PlotLine(parent, *args, **kwargs)
        self.widget = self.figure.native

    def plot(self, x, y, repaint: bool = True, **kwargs):
        """Simple line plot."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)

            try:
                self.update(x, y, repaint=repaint, **kwargs)
            except (AttributeError, OverflowError):
                self.figure.clear()
                self.figure.plot_1d(x, y, **kwargs)

                # set data
                self._data.update(x=x, y=y)

    def update(self, x, y, **kwargs):
        """Update plot without having to clear it."""
        self.set_labels(**kwargs)

        # update plot
        self.figure.plot_1d_update_data(x, y, **kwargs)
        #         self.figure.set_xy_line_limits(reset_y=True)

        # set data
        self._data.update(x=x, y=y)

    def reset(self):
        """Resets the image."""
        self.light_clear()

        if "x" not in self._data or "y" not in self._data:
            return
        # show base image
        self.plot(self._data["x"], self._data["y"], **self._plt_kwargs)

    def add_line(self, x, y, color: str = "r", gid: str = "gid", zorder: int = 5, repaint: bool = True):
        """Add line."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_add(x, y, color=color, gid=gid, zorder=zorder)

    def add_centroids(self, x: np.ndarray, y: np.ndarray, gid: str, repaint: bool = True):
        """Add centroid."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_centroid(x, y, gid=gid)

    def remove_line(self, gid: str, repaint: bool = True):
        """Remove line."""
        with QMutexLocker(MUTEX):
            try:
                self.figure.plot_1d_remove(gid)
            except AttributeError:
                pass

    def update_line_color(self, gid: str, color: str, repaint: bool = True):
        """Update line color."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_color(color, gid)

    def update_line_width(self, width: float = 1.0, gid: Optional[str] = None, repaint: bool = True):
        """Update line width."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_width(width, gid)

    def update_line_style(self, style: str = "solid", gid: Optional[str] = None, repaint: bool = True):
        """Update line style."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_style(style, gid)

    def update_line_alpha(self, alpha: float = 1.0, gid: Optional[str] = None, repaint: bool = True):
        """Update line style."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_alpha(alpha, gid)

    def _update(self):
        """Update plot with current data."""
        with QMutexLocker(MUTEX):
            self.update(self._data["x"], self._data["y"], **self._plt_kwargs)


class ViewVispyScatter(ViewVispyLine):
    """View."""

    PLOT_TYPE = "scatter"
    IS_VISPY = True

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.PLOT_ID = get_short_hash()
        self.figure = PlotScatter(parent, *args, facecolor="black", **kwargs)
        self.widget = self.figure.native

    def plot(self, x, y, repaint: bool = True, forced_kwargs=None, **kwargs):
        """Simple line plot."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)

            try:
                self.update(x, y, repaint=repaint, **kwargs)
            except (AttributeError, OverflowError):
                self.figure.clear()
                self.figure.plot_scatter(
                    x, y, x_label=self.x_label, y_label=self.y_label, callbacks=self._callbacks, **kwargs
                )
                self.figure.repaint(repaint)

                # set data
                self._data.update(x=x, y=y)

    def update(self, x, y, repaint: bool = True, **kwargs):
        """Update."""
        self.set_labels(**kwargs)

        # update plot
        self.figure.update_scatter(x, y, **kwargs)
        self.figure.repaint(repaint)
