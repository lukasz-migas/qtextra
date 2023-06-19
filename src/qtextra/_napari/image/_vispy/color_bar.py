"""Matplotlib-based colorbar.

This implementation is based on one provided in seismic-canvas project

https://github.com/yunzhishi/seismic-canvas/blob/master/seismic_canvas/colorbar_MPL.py

Minor changes were made to make sure values can be easily updated and old unused figures are closed
"""
import io
from typing import Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from koyo.utilities import chunks
from matplotlib.colors import LinearSegmentedColormap
from vispy.color import get_colormap
from vispy.scene.visuals import Image
from vispy.util.dpi import get_dpi
from vispy.util.event import Event

from qtextra.utils.color import hex_to_rgb


def make_vispy_colormap(cmap: str) -> LinearSegmentedColormap:
    """Get colormap from vispy."""
    if cmap.startswith("#"):
        return make_rgb_colormap(hex_to_rgb(cmap))
    # Convert cmap and clim to Matplotlib format.
    cmap = get_colormap(cmap)
    rgba = cmap.colors.rgba
    # Blend to white to avoid this Matplotlib rendering issue:
    # https://github.com/matplotlib/matplotlib/issues/1188
    for i in range(3):
        rgba[:, i] = (1 - rgba[:, -1]) + rgba[:, -1] * rgba[:, i]
    rgba[:, -1] = 1.0
    if len(rgba) < 2:  # in special case of 'grays' cmap!
        rgba = np.array([[0, 0, 0, 1.0], [1, 1, 1, 1.0]])
    return LinearSegmentedColormap.from_list("vispy_cmap", rgba)


def make_rgb_colormap(color: Tuple, n_bins=255) -> LinearSegmentedColormap:
    """Make RGB colormap."""
    lin_range = np.linspace(0, 1.0, n_bins)
    array = np.zeros((n_bins, 3))
    array[:, 0] = lin_range * color[0]
    array[:, 1] = lin_range * color[1]
    array[:, 2] = lin_range * color[2]
    return LinearSegmentedColormap.from_list("vispy_cmap", array)


def render_image(fig, dpi: float) -> np.ndarray:
    """Render image and write it to io buffer."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=dpi, transparent=True)
    buf.seek(0)
    im = plt.imread(buf)
    plt.close(fig)
    return im


class ColorBar(Image):
    """A colorbar visual fixed to the right side of the canvas.

    This is based on the rendering from Matplotlib, then display this rendered image as a scene.visuals.
    Image visual node on the canvas.
    """

    def __init__(
        self,
        size=(500, 10),
        cmap="grays",
        pos=(0, 0),
        clim=(0, 1),
        tick_size: float = 10,
        tick_color: str = "#FFFFFF",
        border_width: float = 1.0,
        border_color: str = "#FFFFFF",
        parent=None,
    ):
        Image.__init__(self, parent=parent, interpolation="nearest", method="auto")
        self.unfreeze()
        # Record the important drawing parameters.
        self.pos = pos
        self.bar_size = size  # tuple
        self._cmap = get_colormap(cmap)  # vispy Colormap
        #         self._clim = clim  # tuple

        self._tick_size = tick_size
        self._tick_color = tick_color
        self._border_width = border_width
        self._border_color = border_color

        # attribute where its possible to temporarily store image data - generation of the colorbar is quite slow,
        # so its sometimes necessary to hide the colorbar in which case, any data set via `refresh` will not be set.
        # That data, however, can be stored for future update which will happen when user clicks on the visibility
        # button
        self._cached_colorbar_data = False
        self._colorbar_data = [
            #             [(1, 0, 0), f"500.413 m/z ± 5 ppm", (0, 100)],
            #             ["#FF0000", f"1500.413 m/z ± 5 ppm", (0, 100, 143)],
            #             [(0, 0, 1), f"312.132 m/z ± 3 ppm", (0, 100)],
        ]
        self.events.add(update_position=Event)

        self.freeze()
        # Draw colorbar using Matplotlib.
        self.refresh()

    @property
    def border_width(self):
        """Border width."""
        return self._border_width

    @border_width.setter
    def border_width(self, value: float):
        self._border_width = value

    @property
    def border_color(self):
        """Border color."""
        return self._border_color

    @border_color.setter
    def border_color(self, value: str):
        self._border_color = value

    @property
    def label_size(self):
        """Border width."""
        return self._tick_size

    @label_size.setter
    def label_size(self, value: float):
        self._tick_size = value

    @property
    def label_color(self):
        """Border color."""
        return self._tick_color

    @label_color.setter
    def label_color(self, value: str):
        self._tick_color = value

    @property
    def cmap(self):
        """Get colormap."""
        return self._cmap

    @cmap.setter
    def cmap(self, value: str):
        self._cmap = get_colormap(value)

    #     @property
    #     def clim(self):
    #         """Colorbar limits"""
    #         return self._clim
    #
    #     @clim.setter
    #     def clim(self, value: Tuple):
    #         self._clim = value

    @property
    def colorbar_data(self):
        """Colorbar data."""
        return self._colorbar_data

    @colorbar_data.setter
    def colorbar_data(self, value):
        self._colorbar_data = value
        if not self.visible:
            self._cached_colorbar_data = True

    #         if not self._colorbar_data:
    #             self.visible = False

    @property
    def visible(self):
        """Visibility."""
        return self._vshare.visible

    @visible.setter
    def visible(self, value):
        if value != self._vshare.visible:
            self._vshare.visible = value
            self.update()

        if self._cached_colorbar_data:
            self.refresh()
            self.events.update_position()
            self._cached_colorbar_data = False

    def refresh(self):
        """Refresh."""
        if self.visible:
            data = self._draw_colorbar()
            if data is not None:
                self.set_data(data)
                self.update()

    def _draw_colorbar(self):
        # should be: label, clim, values
        colorbar_data = self.colorbar_data
        n_rows = len(colorbar_data)
        if n_rows == 0:
            return None
        dpi = get_dpi()

        # calculate figure size
        bar_size = self.bar_size[0] * n_rows, self.bar_size[1]
        figsize = (bar_size[1] / dpi * 2, bar_size[0] / dpi)

        # create normalizer
        norm = mpl.colors.Normalize(vmin=0, vmax=1)

        # create figure
        fig, axs = plt.subplots(ncols=3, nrows=n_rows, figsize=figsize, dpi=dpi)
        axs = axs.flatten()
        for i, axes in enumerate(chunks(axs, 3)):
            _colorbar_data = colorbar_data[i]
            if len(_colorbar_data) == 1:
                color, label, values = _colorbar_data, "", (0, 100)
            elif len(_colorbar_data) == 2:
                color, label = _colorbar_data
                values = (0, 100)
            else:
                color, label, values = colorbar_data[i]
            extend = "neither" if len(values) == 2 else "max"
            # setup colorbar data
            if isinstance(color, str):
                cmap = make_vispy_colormap(color)
            else:
                cmap = make_rgb_colormap(color)

            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)

            # unpack axes
            (ax_label, ax_cb, ax_max) = axes
            [ax.set_axis_off() for ax in [ax_label, ax_max]]

            # create colorbar and stylize it
            cb = fig.colorbar(
                sm,
                cax=ax_cb,
                orientation="horizontal",
                extend=extend,
                extendfrac=0.1,
            )
            cb.set_ticks([0, 1])
            cb.set_ticklabels([f"{v}%" for v in values[0:2]])
            cb.outline.set_linewidth(self.border_width)
            cb.outline.set_edgecolor(self.border_color)
            cb.ax.tick_params(width=self.border_width, labelsize=self.label_size, color=self.border_color)
            plt.setp(plt.getp(cb.ax.axes, "xticklabels"), fontsize=self.label_size, color=self.label_color)

            # set m/z label
            if label != "":
                ax_label.text(
                    -0.05,
                    0.5,
                    label,
                    fontsize=self.label_size,
                    transform=ax_cb.transAxes,
                    ha="right",
                    va="center",
                    color=self.label_color,
                )
            # set extra label
            if len(values) == 3:
                ax_max.text(
                    1.05,
                    0.5,
                    f"{values[2]}%",
                    transform=ax_cb.transAxes,
                    fontsize=self.label_size,
                    ha="left",
                    va="center",
                    color=self.label_color,
                )
            if i != n_rows - 1:
                cb.set_ticks([])
        plt.close(fig)
        return render_image(fig, dpi)
