"""Views base."""

from __future__ import annotations

import time
import typing as ty

from koyo.timer import report_time
from loguru import logger
from qtpy.QtCore import QMutex, QMutexLocker

from qtextra.helpers import get_save_filename

MUTEX = QMutex()


class ViewBase:
    """View base."""

    DEFAULT_PLOT = None
    PLOT_ID = None
    UPDATE_STYLES = ()
    ALLOWED_PLOTS = ()
    SUPPORTED_FILE_FORMATS = ("png", "eps", "jpeg", "tiff", "raw", "ps", "pdf", "svg", "svgz")
    PLOT_TYPE = None
    IS_VISPY = False

    # ui elements
    lock_plot_check = None
    resize_plot_check = None

    def __init__(self, parent, title="", **kwargs):
        self.parent = parent
        self.axes_size = kwargs.pop("axes_size", None)
        self.title = title
        self.filename = kwargs.pop("filename", "")
        self.main_parent = kwargs.pop("main_parent", self)

        self.MPL_KEYS = []
        self.DATA_KEYS = []
        self.FORCED_KWARGS = {}

        # ui elements
        self.figure = None

        # process settings
        self._allow_extraction = kwargs.pop("allow_extraction", False)
        self._callbacks = kwargs.pop("callbacks", {})
        self.FORCED_KWARGS.update(**kwargs.get("FORCED_KWARGS", {}))

        # user settings
        self._x_label = kwargs.pop("x_label", None)
        self._y_label = kwargs.pop("y_label", None)
        self._data = {}
        self._plt_kwargs = {}
        self.style = "default"

    def __repr__(self):
        return f"{self.__class__.__name__}<title={self.title}>"

    @property
    def is_vispy(self) -> bool:
        return self.IS_VISPY

    def unregister(self):
        """Unregister."""

    def plot(self, *args, **kwargs):
        """Simple plot."""
        raise NotImplementedError("Must implement method")

    def update(self, *args, **kwargs):
        """Quick update."""
        raise NotImplementedError("Must implement method")

    def _update(self):
        raise NotImplementedError("Must implement method")

    def has_figure(self) -> bool:
        """Returns boolean to indicate whether figure has been plotted."""
        return self.figure is not None and hasattr(self.figure, "_ax") and self.figure._ax is not None

    def repaint(self, repaint: bool = True):
        """Repaint plot."""
        self.figure.repaint(repaint)

    def clear(self) -> None:
        """Clear plot."""
        with QMutexLocker(MUTEX):
            self.figure.clear()

        # clear old data
        self._data.clear()
        self.figure.PLOT_TYPE = None

    def light_clear(self) -> None:
        """Surface-only clear of the plot without resetting the data."""
        with QMutexLocker(MUTEX):
            self.figure.clear()

    def copy_to_clipboard(self):
        """Copy plot to clipboard."""
        return self.figure.copy_to_clipboard()

    @property
    def callbacks(self):
        """Return list of callbacks associated with the figure."""
        return self._callbacks

    @callbacks.setter
    def callbacks(self, value):
        self._callbacks = value

    @property
    def x_label(self):
        """Return x-axis label."""
        return self._x_label

    @x_label.setter
    def x_label(self, value):
        if value == self._x_label:
            return
        self._x_label = value
        if hasattr(self.figure, "x_axis"):
            self.figure.x_axis.axis.axis_label = value
        self._update()

    @property
    def y_label(self):
        """Return y-axis label."""
        return self._y_label

    @y_label.setter
    def y_label(self, value):
        if value == self._y_label:
            return
        self._y_label = value
        if hasattr(self.figure, "y_axis"):
            self.figure.y_axis.axis.axis_label = value
        self._update()

    def set_labels(self, **kwargs):
        """Update plot labels without triggering replot."""

        def remove_keys(key):
            """Remove key from kwargs."""
            if key in kwargs:
                del kwargs[key]

        x_label = kwargs.pop("x_label", self._x_label)
        y_label = kwargs.pop("y_label", self._y_label)

        self._x_label = x_label
        self._y_label = y_label
        remove_keys("x_label"), remove_keys("y_label"), remove_keys("z_label")

    def set_xlim(self, x_min: float, x_max: float, repaint: bool = True):
        """Set x-axis limits in the plot area."""
        with QMutexLocker(MUTEX):
            self.figure.on_zoom_x_axis(x_min, x_max)
            self.figure.repaint(repaint)

    def get_xlim(self) -> tuple[float, float]:
        """Get x-axis limits."""
        return self.figure.get_xlim()

    def get_current_xlim(self) -> tuple[float, float]:
        """Get x-axis limits."""
        return self.figure.get_current_xlim()

    def get_ylim(self) -> tuple[float, float]:
        """Get x-axis limits."""
        return self.figure.get_ylim()

    def get_current_ylim(self) -> tuple[float, float]:
        """Get x-axis limits."""
        return self.figure.get_current_ylim()

    def set_ylim(self, y_min: float, y_max: float, repaint: bool = True):
        """Set x-axis limits in the plot area."""
        with QMutexLocker(MUTEX):
            self.figure.on_zoom_y_axis(y_min, y_max)
            self.figure.repaint(repaint)

    def update_xlim(self, x_min: float, x_max: float, repaint: bool = True):
        """Set x-axis limits in the plot area and update the extents."""
        with QMutexLocker(MUTEX):
            self.figure.on_set_x_axis(x_min, x_max)
            self.figure.repaint(repaint)

    def set_xylim(self, x_min: float, x_max: float, y_min: float, y_max: float):
        """Set xy-axis limits in the plot area."""
        with QMutexLocker(MUTEX):
            self.figure.on_zoom_xy_axis(x_min, x_max, y_min, y_max)
            self.figure.repaint()

    def get_xy_limits(self):
        """Get x/y-axis limits."""
        return self.figure.get_xy_limits()

    def get_xy_zoom(self):
        """Get x/y-axis limits."""
        return self.figure.get_xy_zoom()

    def clear_annotations(self, repaint: bool = True):
        """Clear ALL annotations from the plot."""
        with QMutexLocker(MUTEX):
            self.figure.plot_remove_patches()
            self.figure.repaint(repaint)

    def add_patch(
        self,
        x: float,
        y: float,
        width: float,
        height: ty.Optional[float] = None,
        color="r",
        obj_name: ty.Optional[str] = None,
        pickable: bool = True,
        repaint: bool = True,
    ):
        """Add rectangular patch to the plot."""
        with QMutexLocker(MUTEX):
            self.figure.plot_add_patch(x, y, width, height, obj_name=obj_name, color=color, pickable=pickable)
            self.figure.repaint(repaint)

    def update_patch(
        self,
        obj_name: str,
        color: ty.Optional[str] = None,
        x: ty.Optional[float] = None,
        y: ty.Optional[float] = None,
        width: ty.Optional[float] = None,
        height: ty.Optional[float] = None,
        repaint: bool = True,
    ):
        """Update patch."""
        with QMutexLocker(MUTEX):
            patch = self.figure.get_existing_patch(obj_name)
            if patch:
                if color:
                    patch.set_facecolor(color)
                if x:
                    patch.set_x(x)
                if y:
                    patch.set_y(y)
                if width is not None:
                    patch.set_width(width)
                if height is not None:
                    patch.set_height(height)
                self.figure.repaint(repaint)

    def move_patch(
        self,
        obj_name: str,
        x: float,
        y: float,
        width: ty.Optional[float] = None,
        height: ty.Optional[float] = None,
        repaint: bool = True,
    ):
        """Move rectangular patch to new position - usually used to indicate region of interest."""
        with QMutexLocker(MUTEX):
            patch = self.figure.get_existing_patch(obj_name)
            if patch is not None:
                patch.set_xy((x, y))
                if width is not None:
                    patch.set_width(width)
                if height is not None:
                    patch.set_height(height)
                self.figure.repaint(repaint)

    def show_patch(
        self,
        x: float,
        y: float,
        width: float,
        height: ty.Optional[float],
        color="r",
        obj_name: ty.Optional[str] = None,
        pickable: bool = True,
        repaint: bool = True,
    ):
        """Show patch - ensure there are no other patches."""
        with QMutexLocker(MUTEX):
            self.figure.plot_remove_patches()
            patch = self.figure.plot_add_patch(x, y, width, height, color=color, obj_name=obj_name, pickable=pickable)
            self.figure.repaint(repaint)
        return patch

    def add_patches(self, x, y, width, height, obj_name=None, color=None, pickable: bool = True, repaint: bool = True):
        """Add rectangular patches to the plot."""
        assert len(x) == len(y) == len(width), "Incorrect shape of the data. `x, y, width` must have the same length"
        if obj_name is None:
            obj_name = [None] * len(x)
        if color is None:
            color = ["r"] * len(x)
        for _x, _y, _width, _height, _obj_name, _color in zip(x, y, width, height, obj_name, color):
            self.figure.plot_add_patch(_x, _y, _width, _height, obj_name=_obj_name, color=_color, pickable=pickable)
        self.figure.repaint(repaint)

    def remove_patches(self, start_with: ty.Optional[str] = None, repaint: bool = True):
        """Remove rectangular patches from the plot.

        Parameters
        ----------
        start_with : str
            name the desired object starts with
        repaint : bool
            flag to repaint (or not) the plot
        """
        with QMutexLocker(MUTEX):
            self.figure.plot_remove_patches(start_with, False)
            self.figure.repaint(repaint)

    def update_roi_shape(self, roi_shape: str):
        """Update ROI shape."""
        if self.figure and hasattr(self.figure.zoom, "update_roi_shape"):
            self.figure.zoom.update_roi_shape(roi_shape)

    def on_lock_plot(self, value):
        """Lock plot interaction."""
        if self.figure and hasattr(self.figure.zoom, "lock"):
            self.figure.zoom.lock = value

    def add_vline(self, xpos: float = 0, gid: str = "ax_vline", repaint: bool = True, **kwargs: ty.Any):
        """Add vline."""
        self.figure.remove_gid(gid)
        self.figure.plot_add_vline(xpos=xpos, gid=gid, **kwargs)
        self.figure.repaint(repaint)

    def add_varrow(self, xpos: float = 0, gid: str = "ax_varrow", repaint: bool = True):
        """Add vline."""
        self.figure.remove_gid(gid)
        self.figure.plot_add_varrow(xpos=xpos, gid=gid)
        self.figure.repaint(repaint)

    def add_vlines(self, vlines: float = 0, gid="vlines", color: str = "k", repaint: bool = True):
        """Add vline."""
        self.figure.remove_gid(gid)
        self.figure.plot_add_vlines(vlines, gid=gid, color=color)
        self.figure.repaint(repaint)

    def remove_vline(self):
        """Remove vline."""
        self.figure.plot_remove_line("ax_vline")
        self.figure.repaint()

    def add_hline(self, ypos: float = 0):
        """Add hline."""
        self.figure.plot_add_hline(ypos=ypos, gid="ax_hline")
        self.figure.repaint()

    def remove_hline(self):
        """Remove hline."""
        self.figure.plot_remove_line("ax_hline")
        self.figure.repaint()

    def reset_limits(self, reset_x: bool = True, reset_y: bool = True, repaint: bool = True):
        """Reset x/y-axis limits."""
        with QMutexLocker(MUTEX):
            self.figure.reset_limits(reset_x, reset_y, repaint)

    def on_zoom_out(self):
        """Zoom out."""
        with QMutexLocker(MUTEX):
            self.figure.on_reset_zoom()

    def on_save_figure(
        self,
        filename="",
        path=None,
        transparent: bool = False,
        dpi: int = 150,
        tight: bool = True,
        black: bool = True,
        **kwargs,
    ):
        """Export figure."""
        if not hasattr(self.figure, "savefig"):
            logger.warning("This view does not implement `savefig` option yet")
            return

        if path is None:
            path = get_save_filename(
                self.parent, "Save figure...", file_filter=build_wildcard(self.SUPPORTED_FILE_FORMATS)
            )

        if path is None or path == "":
            return
        t_start = time.time()

        self.figure.savefig(
            path=path,
            transparent=transparent,
            dpi=dpi,
            tight=tight,
            facecolor="black" if black else "auto",
        )
        logger.info(f"Saved figure in {report_time(t_start)}")

    def has_plot(self) -> bool:
        """Checks whether there is a plot in the figure."""
        return self.figure and self.figure._ax is not None


def build_wildcard(supported_formats) -> str:
    """Build export wildcard."""
    _wildcards = {
        "png": "PNG Portable Network Graphic (*.png)",
        "eps": "Enhanced Windows Metafile (*.eps)",
        "jpeg": "JPEG File Interchange Format (*.jpeg)",
        "tiff": "TIFF Tag Image File Format (*.tiff)",
        "raw": "RAW Image File Format (*.raw)",
        "ps": "PS PostScript Image File Format (*.ps)",
        "pdf": "PDF Portable Document Format (*.pdf)",
        "svg": "SVG Scalable Vector Graphic (*.svg)",
        "svgz": "SVGZ Compressed Scalable Vector Graphic (*.svgz)",
    }

    wildcard = ""
    n_formats = len(supported_formats) - 1
    for i, fmt in enumerate(supported_formats):
        value = _wildcards[fmt]
        if i < n_formats:
            value += ";;"
        wildcard += value
    return wildcard
