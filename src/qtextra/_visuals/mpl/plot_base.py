"""Base class for all mpl-based plotting functionality."""

import typing as ty
from contextlib import contextmanager, suppress

import matplotlib
import matplotlib.cm as cm
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from koyo.utilities import get_min_max
from koyo.visuals import find_text_color, get_intensity_formatter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QApplication, QHBoxLayout, QSizePolicy, QWidget

from qtextra._visuals.mpl.gids import PlotIds
from qtextra._visuals.mpl.interaction import ImageMPLInteraction, MPLInteraction
from qtextra.utils.utilities import connect

try:
    import seaborn as sns
except ImportError:
    sns = None

if ty.TYPE_CHECKING:
    import pandas as pd

from loguru import logger

try:
    matplotlib.use("Qt5Agg")
except ImportError:
    print("Failed to load qt5 backend")
matplotlib.rcParams["agg.path.chunksize"] = 10000


def make_centroid_lines(x: np.ndarray, y: np.ndarray):
    """Make centroids."""
    lines = []
    for i in range(len(x)):
        pair = [(x[i], 0), (x[i], y[i])]
        lines.append(pair)
    return lines


class PlotBase(QWidget):
    """Generic plot base."""

    evt_unregister = Signal()

    evt_pick = Signal()
    evt_move = Signal(tuple)
    evt_wheel = Signal()
    evt_pressed = Signal()
    evt_double_click = Signal()
    evt_released = Signal()
    evt_ctrl_changed = Signal(bool)
    evt_ctrl_released = Signal(tuple)
    evt_ctrl_double_click = Signal(tuple)

    PLOT_TYPE = None
    MPL_STYLE = "seaborn-v0_8-ticks"

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent=parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # extract various variables
        self.plot_id = kwargs.pop("plot_id", "")
        self.window_name = kwargs.pop("window_name", None)
        self.main_parent = kwargs.pop("main_parent", None)

        self.figsize = kwargs.pop("figsize", None)
        if self.figsize is None:
            self.figsize = [8, 8]

        # ensure minimal figure size
        if self.figsize[0] <= 0:
            self.figsize[0] = 1.0
        if self.figsize[1] <= 0:
            self.figsize[1] = 1.0

        self.facecolor = kwargs.get("facecolor", "white")
        self.zoom_color = kwargs.pop("zoom_color", Qt.GlobalColor.black)
        # setup figure
        self.figure = Figure(facecolor=self.facecolor, dpi=100, figsize=self.figsize)
        self.canvas = FigureCanvasQTAgg(figure=self.figure)
        # This is necessary to ensure keyboard events work
        self.canvas.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.canvas.setFocus()

        # RESIZE
        sizer = QHBoxLayout(self)
        sizer.setContentsMargins(0, 0, 0, 0)
        sizer.setSpacing(0)
        sizer.addWidget(self.canvas, stretch=1)

        self._ax = None
        # Prepare for zoom
        self.zoom = None
        self._disable_repaint = False
        self._repaint = True

        # obj containers
        self.text = []
        self.lines = []
        self.patch = []
        self.markers = []
        self.arrows = []

        # occasionally used to tag to mark what plot was used previously
        self.plot_name = ""
        self.y_divider = 1

    def add_zoom(self):
        """Add zoom."""
        extent = get_extent(self.ax)
        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)
        self.store_plot_limits([extent], [self.ax])

    def plot_precision_recall_fscore_support(
        self,
        scores: dict,
        labels: list[str],
        cmap: str = "Blues",
        cmap_undercolor: str = "w",
        cmap_overcolor: str = "#2a7d4f",
        title: str = "Classification Report",
        title_fontsize="large",
        text_fontsize="medium",
        **kwargs,
    ):
        """Renders the classification report across each axis."""
        cmap = cm.get_cmap(cmap).copy()
        cmap.set_over(color=cmap_overcolor)
        cmap.set_under(color=cmap_undercolor)

        # Create display grid
        cr_display = np.zeros((len(labels), len(scores)))

        # For each class row, append columns for precision, recall, f1, and support
        for idx, cls in enumerate(labels):
            for jdx, metric in enumerate(scores):
                cr_display[idx, jdx] = scores[metric][cls]

        # Set up the dimensions of the pcolormesh
        # NOTE: pcolormesh accepts grids that are (N+1,M+1)
        X, Y = (np.arange(len(labels) + 1), np.arange(len(scores) + 1))
        self.ax.set_ylim(bottom=0, top=cr_display.shape[0])
        self.ax.set_xlim(left=0, right=cr_display.shape[1])

        # Fetch the grid labels from the classes in correct order; set ticks.
        x_tick_labels = list(scores.keys())
        y_tick_labels = labels

        y_ticks = np.arange(len(labels)) + 0.5
        x_ticks = np.arange(len(scores)) + 0.5

        self.ax.set(yticks=y_ticks, xticks=x_ticks)
        self.ax.set_xticklabels(x_tick_labels, fontsize=text_fontsize)
        self.ax.set_yticklabels(y_tick_labels, fontsize=text_fontsize)

        # Set data labels in the grid, enumerating over class, metric pairs
        # NOTE: X and Y are one element longer than the classification report
        # so skip the last element to label the grid correctly.
        for x in X[:-1]:
            for y in Y[:-1]:
                # Extract the value and the text label
                value = cr_display[x, y]

                # Determine the grid and text colors
                base_color = cmap(value)
                text_color = find_text_color(base_color)

                # Add the label to the middle of the grid
                cx, cy = x + 0.5, y + 0.5
                self.ax.text(cy, cx, f"{value:0.3f}", va="center", ha="center", color=text_color)

        # Draw the heatmap with colors bounded by the min and max of the grid
        # NOTE: I do not understand why this is Y, X instead of X, Y it works
        # in this order but raises an exception with the other order.
        self.ax.pcolormesh(Y, X, cr_display, vmin=0, vmax=1, cmap=cmap, edgecolor="w")
        self.ax.set_title(title, fontsize=title_fontsize)

    def plot_confusion_matrix(
        self,
        matrix: np.ndarray,
        labels: list[str],
        which: str = "counts",
        title: str = "Confusion Matrix",
        title_fontsize="large",
        text_fontsize="medium",
        **kwargs,
    ):
        """Plot confusion matrix."""
        if not sns:
            raise ImportError("Seaborn is required for this function")
        ax = self.ax
        if which == "counts":
            sns.heatmap(data=matrix, ax=ax, square=True, annot=True, fmt="d", **kwargs)
        elif which == "percentage":
            sns.heatmap(data=matrix / np.sum(matrix), ax=ax, square=True, annot=True, fmt=".2%", **kwargs)
        else:
            group_counts = [f"{value:0.0f}" for value in matrix.flatten()]
            group_percentages = [f"{value:.2%}" for value in matrix.flatten() / np.sum(matrix)]
            matrix_labels = [f"{v1}\n{v2}\n" for v1, v2 in zip(group_counts, group_percentages)]
            matrix_labels = np.asarray(matrix_labels).reshape(matrix.shape)
            sns.heatmap(matrix, ax=ax, square=True, annot=matrix_labels, fmt="")

        ax.set_title(title, fontsize=title_fontsize)
        ax.xaxis.set_ticklabels(labels)
        ax.yaxis.set_ticklabels(labels)
        ax.tick_params(labelsize=text_fontsize)
        ax.set_xlabel("\nPredicted", fontsize=text_fontsize)
        ax.set_ylabel("Actual", fontsize=text_fontsize)

        extent = get_extent(self.ax)
        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)
        self.store_plot_limits([extent], [self.ax])

    def plot_roc(
        self,
        fpr: dict[str, np.ndarray],
        tpr: dict[str, np.ndarray],
        labels: dict[str, np.ndarray],
        plot_micro: bool = True,
        plot_macro: bool = True,
        title: str = "ROC Curves",
        title_fontsize="large",
        text_fontsize="medium",
        **kwargs,
    ):
        """Plot ROC."""
        if not sns:
            raise ImportError("Seaborn is required for this function")
        ax = self.ax
        i = 0
        colors = sns.color_palette(n_colors=len(fpr))
        for key in fpr.keys():
            if key == "micro" and plot_micro:
                ax.plot(fpr[key], tpr[key], color="deeppink", linestyle=":", linewidth=4, label=labels[key])
            elif key == "macro" and plot_macro:
                ax.plot(fpr[key], tpr[key], color="navy", linestyle=":", linewidth=4, label=labels[key])
            else:
                ax.plot(fpr[key], tpr[key], lw=2, color=colors[i], label=labels[key])
                i += 1

        ax.set_title(title, fontsize=title_fontsize)
        ax.plot([0, 1], [0, 1], "k--", lw=2)
        ax.set_xlim([-0.05, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel("False Positive Rate", fontsize=text_fontsize)
        ax.set_ylabel("True Positive Rate", fontsize=text_fontsize)
        ax.tick_params(labelsize=text_fontsize)
        ax.legend(loc="lower right", fontsize=text_fontsize)

        extent = get_extent(self.ax)
        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)
        self.store_plot_limits([extent], [self.ax])

    def plot_precision_recall(
        self,
        precision: dict[str, np.ndarray],
        recall: dict[str, np.ndarray],
        labels: dict[str, np.ndarray],
        plot_micro: bool = True,
        title: str = "Precision-Recall Curve",
        title_fontsize="large",
        text_fontsize="medium",
        **kwargs,
    ):
        """Plot Precision-Recall."""
        if not sns:
            raise ImportError("Seaborn is required for this function")
        ax = self.ax
        i = 0
        colors = sns.color_palette(n_colors=len(precision))
        for key in precision.keys():
            if key == "micro" and plot_micro:
                ax.plot(recall[key], precision[key], lw=4, linestyle=":", color="navy", label=labels[key])
            else:
                ax.plot(recall[key], precision[key], lw=2, color=colors[i], label=labels[key])
                i += 1

        ax.set_title(title, fontsize=title_fontsize)
        ax.set_xlim([0.0, 1.05])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.tick_params(labelsize=text_fontsize)
        ax.legend(loc="best", fontsize=text_fontsize)

        extent = get_extent(self.ax)
        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)
        self.store_plot_limits([extent], [self.ax])

    def plot_violin(self, df: "pd.DataFrame", **kwargs):
        """Plot violin plot."""
        if not sns:
            raise ImportError("Seaborn is required for this function")

        sns.violinplot(data=df, ax=self.ax, **kwargs)

        extent = get_extent(self.ax)
        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)
        self.store_plot_limits([extent], [self.ax])

    def plot_boxplot(self, df: "pd.DataFrame", **kwargs):
        """Plot violin plot."""
        if not sns:
            raise ImportError("Seaborn is required for this function")
        sns.boxplot(data=df, ax=self.ax, **kwargs)

        extent = get_extent(self.ax)
        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)
        self.store_plot_limits([extent], [self.ax])

    def plot_boxenplot(self, df: "pd.DataFrame", **kwargs):
        """Plot boxenplot plot."""
        if not sns:
            raise ImportError("Seaborn is required for this function")

        sns.boxenplot(data=df, ax=self.ax, **kwargs)
        extent = get_extent(self.ax)

        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)

        # Setup extents
        self.store_plot_limits([extent], [self.ax])

    def plot_stripplot(self, df: "pd.DataFrame", **kwargs):
        """Plot stripplot plot."""
        if not sns:
            raise ImportError("Seaborn is required for this function")
        sns.stripplot(data=df, ax=self.ax, **kwargs)
        extent = get_extent(self.ax)

        self.setup_new_zoom([self.ax], data_limits=[extent], allow_extraction=False)

        # Setup extents
        self.store_plot_limits([extent], [self.ax])

    @staticmethod
    def _compute_xy_limits(
        x: ty.Union[list, np.ndarray],
        y: ty.Union[list, np.ndarray],
        y_lower_start: ty.Optional[float] = 0,
        y_upper_multiplier: float = 1,
        is_heatmap: bool = False,
        x_pad=None,
        y_pad=None,
        y_lower_multiplier: float = 1,
    ):
        """Calculate the x/y axis ranges."""
        x = np.nan_to_num(x)
        y = np.nan_to_num(y)
        x_min, x_max = get_min_max(x)
        y_min, y_max = get_min_max(y)

        if is_heatmap:
            x_min, x_max = x_min, x_max + 1
            y_min, y_max = y_min, y_max + 1

        if x_pad is not None:
            x_min, x_max = x_min - x_pad, x_max + x_pad

        if y_pad is not None:
            y_min, y_max = y_min - y_pad, y_max + y_pad

        x_limit = [x_min, x_max]
        if y_lower_start is None:
            y_lower_start = y_min
        y_limit = [y_lower_start * y_lower_multiplier, y_max * y_upper_multiplier]

        # extent is x_min, y_min, x_max, y_max
        extent = [x_limit[0], y_limit[0], x_limit[1], y_limit[1]]
        return x_limit, y_limit, extent

    def _get_extent(self, xmin, xmax, ymin, ymax):
        """Get extent."""
        return [xmin, ymin, xmax, ymax]

    def get_xy_limits(self) -> list[float]:
        """Get x- and y-axis limits that are currently shown in the plot."""
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()

        return [xmin, xmax, ymin, ymax]

    def on_zoom_x_axis(self, start_x=None, end_x=None):
        """Horizontal zoom."""
        _start_x, _end_x, _, _ = self.get_xy_limits()
        if start_x is None:
            start_x = _start_x
        if end_x is None:
            end_x = _end_x
        self.ax.set_xlim([start_x, end_x])

    def on_zoom_y_axis(self, start_y=None, end_y=None):
        """Horizontal zoom."""
        _, _, _start_y, _end_y = self.get_xy_limits()
        if start_y is None:
            start_y = _start_y
        if end_y is None:
            end_y = _end_y
        self.ax.set_ylim([start_y, end_y])

    def on_set_x_axis(self, start_x=None, end_x=None):
        """Horizontal zoom."""
        _start_x, _end_x, _, _ = self.get_xy_limits()
        if start_x is None:
            start_x = _start_x
        if end_x is None:
            end_x = _end_x

        # update plot limits
        self.ax.set_xlim([start_x, end_x])
        start_y, end_y = self.get_ylim()
        extent = self._get_extent(start_x, end_x, start_y, end_y)

        self.update_extents([extent])
        self.store_plot_limits([extent], [self.ax])

    def on_zoom_xy_axis(self, start_x: float, end_x: float, start_y: float, end_y: float):
        """Horizontal and vertical zoom."""
        _start_x, _end_x, _start_y, _end_y = self.get_xy_limits()
        if start_x is None:
            start_x = _start_x
        if end_x is None:
            end_x = _end_x
        if start_y is None:
            start_y = _start_y
        if end_y is None:
            end_y = _end_y
        self.ax.axis([start_x, end_x, start_y, end_y])

    def store_plot_limits(self, extent: list, ax: ty.Optional[list] = None):
        """Setup plot limits."""
        if ax is None:
            ax = [self.ax]

        if not isinstance(ax, list):
            ax = list(ax)

        if len(ax) != len(extent):
            raise ValueError("Could not store plot limits")

        for _ax, _extent in zip(ax, extent):
            _ax.plot_limits = [_extent[0], _extent[2], _extent[1], _extent[3]]

    def set_plot_xlabel(self, xlabel: ty.Optional[str] = None, ax=None, **kwargs):
        """Set plot x-axis label."""
        # kwargs = ut_visuals.check_plot_settings(**kwargs)
        if ax is None:
            ax = self.ax
        if xlabel is None:
            xlabel = ax.get_xlabel()
        ax.set_xlabel(
            xlabel,
            # labelpad=kwargs["axes_label_pad"],
            # fontsize=kwargs["axes_label_font_size"],
            # weight=kwargs["axes_label_font_weight"],
        )
        # self.plot_labels["xlabel"] = xlabel

    def set_plot_ylabel(self, ylabel: ty.Optional[str] = None, ax=None, **kwargs):
        """Set plot y-axis label."""
        # kwargs = ut_visuals.check_plot_settings(**kwargs)
        if ax is None:
            ax = self.ax
        if ylabel is None:
            ylabel = ax.get_ylabel()
        ax.set_ylabel(
            ylabel,
            # labelpad=kwargs["axes_label_pad"],
            # fontsize=kwargs["axes_label_font_size"],
            # weight=kwargs["axes_label_font_weight"],
        )
        # self.plot_labels["ylabel"] = ylabel

    def set_plot_title(self, title: ty.Optional[str] = None, color: str = "black", loc: str = "center", **kwargs):
        """Set plot title."""
        if title is None:
            title = self.ax.get_title()

        self.ax.set_title(
            title,
            color=color,
            loc=loc,
            verticalalignment="baseline",
            fontweight="normal",
            fontsize=14,
            # x=0.01
        )

    def get_plot_limits(self, ax=None):
        """Get plot limits."""
        if ax is None:
            ax = self.ax
        if hasattr(ax, "plot_limits"):
            return ax.plot_limits
        return [*ax.get_xlim(), *ax.get_ylim()]

    def get_xlim(self):
        """Get x-axis limits."""
        plot_limits = self.get_plot_limits()
        return plot_limits[0], plot_limits[1]

    def get_current_xlim(self):
        """Get current x-axis limits."""
        return self.ax.get_xlim()

    def get_current_ylim(self):
        """Get current x-axis limits."""
        return self.ax.get_ylim()

    def get_ylim(self):
        """Get y-axis limits."""
        plot_limits = self.get_plot_limits()
        return plot_limits[2], plot_limits[3]

    def copy_to_clipboard(self):
        """Copy canvas to clipboard."""
        from qtextra.helpers import add_flash_animation

        pixmap = self.canvas.grab()
        QApplication.clipboard().setPixmap(pixmap)
        add_flash_animation(self)
        logger.debug("Figure was copied to the clipboard")

    def on_reset_zoom(self, repaint: bool = True):
        """Reset plot zoom."""
        try:
            start_x, end_x, start_y, end_y = self.get_plot_limits()
            self.ax.set_xlim(start_x, end_x)
            self.ax.set_ylim(start_y, end_y)
            self.repaint(repaint)
        except AttributeError:
            pass

    @staticmethod
    def _check_start_with(obj, start_with: str):
        """Checks whether label starts with specific string."""
        if isinstance(obj.obj_name, str):
            if obj.obj_name.startswith(start_with):
                return True
        return False

    def _remove_existing_patch(self, name_tag: str):
        """Remove patch with specific name tag."""
        for i, patch in enumerate(self.patch):
            if patch.obj_name == name_tag:
                patch.remove()
                del self.patch[i]
                break

    def get_existing_patch(self, name_tag: str) -> mpatches.Rectangle:
        """Retrieve name tag from list of patches."""
        for _i, patch in enumerate(self.patch):
            if patch.obj_name == name_tag:
                return patch

    def plot_add_patch(
        self,
        xmin: float,
        ymin: float,
        width: float,
        height: float,
        color="r",
        alpha: float = 0.5,
        linewidth: float = 0,
        obj_name: str = "",
        pickable: bool = True,
        edgecolor="k",
        **kwargs,
    ):
        """Add patch to the plot area."""
        if obj_name not in [None, ""]:
            self._remove_existing_patch(obj_name)

        # height can be defined as None to force retrieval of the highest value in the plot
        if height in [0, None]:
            height = self.get_ylim()[-1]

        try:
            patch = self.ax.add_patch(
                mpatches.Rectangle(
                    (xmin, ymin),
                    width,
                    height,
                    facecolor=color,
                    alpha=alpha,
                    linewidth=linewidth,
                    picker=pickable,
                    edgecolor=edgecolor,
                )
            )
        except AttributeError:
            logger.warning("Please plot something first")
            return

        # set label
        patch.obj_name = obj_name
        patch.y_divider = self.y_divider
        self.patch.append(patch)
        return patch

    def plot_remove_patches(self, start_with: ty.Optional[str] = None, repaint: bool = True):
        """Remove patch fr-om the plot area."""
        patches = []
        for patch in self.patch:
            if start_with is not None and hasattr(patch, "obj_name"):
                if not self._check_start_with(patch, start_with):
                    patches.append(patch)
                    continue
            try:
                patch.remove()
            except Exception:
                pass

        self.patch = patches
        self.repaint(repaint)

    def plot_add_hline(
        self,
        xmin: float = 0,
        xmax: float = 1,
        ypos: float = 0,
        color: str = "k",
        alpha: float = 0.7,
        gid: str = "ax_hline",
    ):
        """Add horizontal line to the axes."""
        line = self.ax.axhline(ypos, xmin, xmax, color=color, alpha=alpha, gid=gid)
        line.obj_name = gid
        self.lines.append(line)

    def plot_remove_line(self, gid: str):
        """Remove horizontal line."""
        to_remove = []
        for i, line in enumerate(self.lines):
            if line.obj_name == gid:
                with suppress(ValueError):
                    line.remove()
                to_remove.append(i)

        if to_remove:
            for i in reversed(to_remove):
                del self.lines[i]

    def get_line(self, gid: str):
        """Get instance of the line."""
        for line in self.lines:
            if line.obj_name == gid:
                return line
        return None

    def plot_add_vline(
        self,
        xpos: float = 0,
        ymin: float = 0,
        ymax: float = 1,
        color: str = "k",
        alpha: float = 0.5,
        gid: str = "ax_vline",
    ):
        """Add vertical line to the axes."""
        line = self.get_line(gid)
        if line is not None:
            line.set_xdata([xpos, xpos])
            line.set_ydata([ymin, ymax])
        else:
            line = self.ax.axvline(xpos, ymin, ymax, color=color, alpha=alpha, gid=gid)
            line.obj_name = gid
            self.lines.append(line)

    def plot_add_varrow(self, xpos: float, yoffset=-0.05, gid: str = "ax_varrow") -> None:
        """Add arrow below the x-axis line, indicating location."""
        arrow = self.ax.annotate(
            "",
            xy=(xpos, 0),
            xytext=(xpos, yoffset),
            arrowprops={"arrowstyle": "->", "color": "red"},
            gid=gid,
        )
        arrow.obj_name = gid
        self.arrows.append(arrow)

    def plot_add_vlines(
        self, vlines: np.ndarray, ymin: float = 0, color: str = "k", alpha: float = 0.5, ls="--", gid: str = "vlines"
    ):
        """Add vertical lines to the axes."""
        xmax = self.get_xlim()[1]
        vline = self.ax.vlines(vlines, ymin, xmax, color=color, alpha=alpha, ls=ls, gid=gid)
        vline.obj_name = gid

    def is_locked(self):
        """Check whether plot is locked."""
        if self.lock_plot_from_updating:
            self.locked()

    def locked(self):
        """Let user know that the plot is locked."""
        raise ValueError(
            "Plot modification is locked",
            "This plot is locked and you cannot use global setting updated. \n"
            + "Please right-click in the plot area and select Customise plot..."
            + " to adjust plot settings.",
        )

    @property
    def ax(self):
        """Get axes."""
        with plt.style.context(self.MPL_STYLE):
            if self._ax is None:
                self._ax = self.figure.add_axes([0.1, 0.15, 0.87, 0.82])  # left, bottom, width, height
                # self._ax = self.figure.subplots()
            return self._ax

    def __repr__(self):
        return f"Plot: {self.plot_name} | Window name: {self.window_name}"

    def setup_new_zoom(
        self,
        figure,
        data_limits=None,
        allow_extraction=True,
        callbacks=None,
        is_heatmap: bool = False,
        is_joint: bool = False,
        obj=None,
        arrays=None,
    ):
        """Setup the new-style matplotlib zoom."""
        if callbacks is None:
            callbacks = {}

        if self.zoom:
            connect(self.zoom.evt_pick, self.evt_pick.emit, state=False, silent=True)
            connect(self.zoom.evt_pressed, self.evt_pressed.emit, state=False, silent=True)
            connect(self.zoom.evt_released, self.evt_released.emit, state=False, silent=True)
            connect(self.zoom.evt_ctrl_changed, self.evt_ctrl_changed.emit, state=False, silent=True)
            connect(self.zoom.evt_ctrl_released, self.evt_ctrl_released.emit, state=False, silent=True)
            connect(self.zoom.evt_wheel, self.evt_wheel.emit, state=False, silent=True)
            connect(self.zoom.evt_move, self.evt_move.emit, state=False, silent=True)
            connect(self.zoom.evt_ctrl_double_click, self.evt_ctrl_double_click.emit, state=False, silent=True)

        if arrays is None:
            self.zoom = MPLInteraction(
                figure,
                data_limits=data_limits,
                allow_extraction=allow_extraction,
                callbacks=callbacks,
                is_heatmap=is_heatmap,
                is_joint=is_joint,
                obj=obj,
                plot_id=self.plot_id,
                zoom_color=self.zoom_color,
            )

        else:
            self.zoom = ImageMPLInteraction(
                figure,
                arrays,
                data_limits=data_limits,
                allow_extraction=allow_extraction,
                callbacks=callbacks,
                is_heatmap=is_heatmap,
                is_joint=is_joint,
                obj=obj,
                plot_id=self.plot_id,
                zoom_color=self.zoom_color,
            )
        connect(self.zoom.evt_pick, self.evt_pressed.emit)
        connect(self.zoom.evt_move, self.evt_move.emit)
        connect(self.zoom.evt_pressed, self.evt_pressed.emit)
        connect(self.zoom.evt_released, self.evt_released.emit)
        connect(self.zoom.evt_ctrl_released, self.evt_ctrl_released.emit)
        connect(self.zoom.evt_wheel, self.evt_wheel.emit)
        connect(self.zoom.evt_double_click, self.evt_double_click.emit)
        connect(self.zoom.evt_ctrl_changed, self.evt_ctrl_changed.emit)
        connect(self.zoom.evt_ctrl_double_click, self.evt_ctrl_double_click.emit)

    def update_extents(self, extents: list, obj=None, arrays=None):
        """Update plot extents."""
        if self.zoom is not None:
            self.zoom.update_handler(data_limits=extents, obj=obj, arrays=arrays)

    def update_roi_shape(self, roi_shape: str):
        """Set ROI shape."""
        if self.zoom is not None:
            self.zoom.update_roi_shape(roi_shape)

    @contextmanager
    def delayed_repaint(self) -> None:
        """Temporarily disable repainting."""
        self._disable_repaint = True
        yield
        self._disable_repaint = False
        self._repaint = True
        self.repaint()

    def repaint(self, repaint: bool = True):
        """Redraw and refresh the plot."""
        if self._disable_repaint:
            return

        if repaint:
            self.canvas.draw()
        self._repaint = False

    def tight(self, tight: bool = True):
        """Tighten layout."""
        if tight:
            self.figure.tight_layout()

    def clear(self):
        """Clear the plot and rest some of the parameters."""
        self._clear()
        self.figure.clear()
        self.zoom = None

        # clear stores
        self.text = []
        self.lines = []
        self.patch = []
        self.markers = []
        self.arrows = []

        # clear plots
        self._ax = None

        self.repaint()

    def _clear(self):
        """Extra clears that subclasses can implement."""

    def savefig(
        self,
        path,
        tight: bool = True,
        dpi: int = 150,
        transparent: bool = True,
        image_fmt: str = "png",
        facecolor: str = "auto",
        resize=None,
    ):
        """Export figure."""
        # TODO: add option to resize the plot area
        if not hasattr(self, "_ax"):
            logger.warning("Cannot save a plot that has not been plotted yet")
            return
        self.figure.savefig(
            path,
            transparent=transparent,
            dpi=dpi,
            format=image_fmt,
            bbox_inches="tight" if tight else None,
            facecolor=facecolor,
        )

    def reset_limits(self, reset_x: bool = True, reset_y: bool = True, repaint: bool = True):
        """Reset x/y-axis limits."""
        self.set_xy_line_limits(reset_x=reset_x, reset_y=reset_y)
        self.repaint(repaint)

    def plot_1d_centroid(
        self,
        x,
        y,
        x_label: str = "",
        y_label: str = "",
        gid=PlotIds.PLOT_1D_CENTROID_GID,
        label="",
        title: str = "",
        y_lower_start=None,
        y_upper_multiplier=1.1,
        line_width: int = 2,
        color="k",
        **kwargs,
    ):
        """Centroids plot."""
        xlimits, ylimits, extent = self._compute_xy_limits(x, y, y_lower_start, y_upper_multiplier)

        xy = make_centroid_lines(x, y)
        line_coll = LineCollection(xy, color=color, linewidth=line_width, gid=gid, label=label)
        self.ax.add_collection(line_coll)

        # setup axis formatters
        self.ax.yaxis.set_major_formatter(get_intensity_formatter())
        self.ax.set_xlim(xlimits)
        self.ax.set_ylim(ylimits)
        self.set_plot_xlabel(x_label, **kwargs)
        self.set_plot_ylabel(y_label, **kwargs)
        self.set_plot_title(title, **kwargs)

        self.setup_new_zoom(
            [self.ax],
            data_limits=[extent],
            allow_extraction=kwargs.get("allow_extraction", True),
            callbacks=kwargs.get("callbacks", {}),
        )

        # Setup X-axis getter
        self.store_plot_limits([extent], [self.ax])
        self.PLOT_TYPE = "line"

    def plot_1d(
        self,
        x,
        y,
        title="",
        x_label="",
        y_label="",
        label="",
        y_lower_start=None,
        y_upper_multiplier=1.1,
        gid=PlotIds.PLOT_1D_LINE_GID,
        color="k",
        zorder: int = 5,
        line_width: int = 1,
        line_alpha: float = 1.0,
        line_style: str = "solid",
        **kwargs,
    ):
        """Standard 1d plot."""
        xlimits, ylimits, extent = self._compute_xy_limits(x, y, y_lower_start, y_upper_multiplier)

        # add 1d plot
        self.ax.plot(
            x, y, color=color, label=label, gid=gid, zorder=zorder, lw=line_width, alpha=line_alpha, ls=line_style
        )
        if kwargs.get("spectrum_line_fill_under", False):
            self.plot_1d_add_under_curve(x, y, **kwargs)

        # setup axis formatters
        self.ax.yaxis.set_major_formatter(get_intensity_formatter())
        self.ax.set_xlim(xlimits)
        self.ax.set_ylim(ylimits)
        self.set_plot_xlabel(x_label, **kwargs)
        self.set_plot_ylabel(y_label, **kwargs)
        self.set_plot_title(title, **kwargs)

        self.setup_new_zoom(
            [self.ax],
            data_limits=[extent],
            allow_extraction=kwargs.get("allow_extraction", True),
            callbacks=kwargs.get("callbacks", {}),
        )

        # Setup X-axis getter
        self.store_plot_limits([extent], [self.ax])
        self.PLOT_TYPE = "line"

    def plot_1d_add_under_curve(self, xvals, yvals, gid=None, ax=None, **kwargs):
        """Fill data under the line."""
        color = kwargs.get("spectrum_fill_color", "k")

        shade_kws = {
            "facecolor": color,
            "alpha": kwargs.get("spectrum_fill_transparency", 0.25),
            "clip_on": kwargs.get("clip_on", True),
            "zorder": kwargs.get("zorder", 1),
            "hatch": kwargs.get("spectrum_fill_hatch", None),
        }
        if ax is None:
            ax = self.ax
        if gid is None:
            gid = PlotIds.PLOT_1D_PATCH_GID
        ax.fill_between(xvals, 0, yvals, gid=gid, **shade_kws)

    def plot_1d_update_data(
        self,
        x,
        y,
        x_label="",
        y_label="",
        y_lower_start=None,
        y_upper_multiplier=1.1,
        ax=None,
        gid=PlotIds.PLOT_1D_LINE_GID,
        line_width: int = 1,
        line_alpha: float = 1.0,
        line_style: str = "solid",
        **kwargs,
    ):
        """Update plot data."""
        # override parameters
        _, _, extent = self._compute_xy_limits(x, y, y_lower_start, y_upper_multiplier)

        if ax is None:
            ax = self.ax

        line = None
        lines = ax.get_lines()
        for line in lines:
            _gid = line.get_gid()
            if _gid == gid:
                break

        if line is None:
            raise ValueError("Could not find line to update")

        line.set_xdata(x)
        line.set_ydata(y)
        line.set_linewidth(line_width)
        line.set_linestyle(line_style)
        line.set_alpha(line_alpha)
        # line.set_color(kwargs["spectrum_line_color"])
        # line.set_label(kwargs.get("label", ""))

        for patch in ax.collections:
            if patch.get_gid() == PlotIds.PLOT_1D_PATCH_GID:
                with suppress(ValueError):
                    patch.remove()
                self.plot_1d_add_under_curve(x, y, ax=ax, **kwargs)

        # general plot updates
        self.set_plot_xlabel(x_label, **kwargs)
        self.set_plot_ylabel(y_label, **kwargs)

        # update plot limits
        self.update_extents([extent])
        self.store_plot_limits([extent], [self.ax])

    def plot_1d_update_x_axis(
        self,
        x: np.ndarray,
        x_label: ty.Optional[str] = None,
        ax=None,
        gid=PlotIds.PLOT_1D_LINE_GID,
    ):
        """Update x-axis."""
        if ax is None:
            ax = self.ax
        line = None
        lines = ax.get_lines()
        for line in lines:
            _gid = line.get_gid()
            if _gid == gid:
                break

        if line is None:
            raise ValueError("Could not find line to update")
        line.set_xdata(x)
        self.set_plot_xlabel(x_label, ax)

    def plot_1d_add(
        self,
        x,
        y,
        color: str = "r",
        gid: str = "gid",
        zorder: int = 5,
        line_width: int = 1,
        line_alpha: float = 1.0,
        line_style: str = "solid",
    ):
        """Add spectrum."""
        self.ax.plot(x, y, color=color, gid=gid, zorder=zorder, lw=line_width, alpha=line_alpha, ls=line_style)

    def plot_1d_update_color(self, gid: str, color):
        """Update plot color."""
        line = self.plot_1d_get_line(gid)
        if line:
            line.set_color(color)

    def plot_1d_update_line_width(self, line_width: float, gid: ty.Optional[str] = None):
        """Update line width."""
        for line in self.ax.get_lines():
            if gid is not None:
                _gid = line.get_gid()
                if gid != _gid:
                    continue
            line.set_linewidth(line_width)

    def plot_1d_update_line_alpha(self, line_alpha: float, gid: ty.Optional[str] = None):
        """Update plot color."""
        for line in self.ax.get_lines():
            if gid is not None:
                _gid = line.get_gid()
                if gid != _gid:
                    continue
            line.set_alpha(line_alpha)

    def plot_1d_update_line_style(self, line_style: str, gid: ty.Optional[str] = None):
        """Update plot color."""
        for line in self.ax.get_lines():
            if gid is not None:
                _gid = line.get_gid()
                if gid != _gid:
                    continue
            line.set_linestyle(line_style)

    def plot_1d_remove(self, gid: str):
        """Remove line."""
        self.plot_remove_line(gid)

    def remove_gid(self, gid: str, kind: str = "any") -> None:
        """Remove any object with specific gid."""
        with suppress(ValueError):
            if kind in ["any", "line"]:
                self.plot_remove_line(gid)
                for line in self.ax.get_lines():
                    _gid = line.get_gid()
                    if gid == _gid:
                        line.remove()
            if kind in ["any", "patch"]:
                for coll in self.ax.collections:
                    _gid = coll.get_gid()
                    if gid == _gid:
                        coll.remove()
                for patch in self.patch:
                    if patch.obj_name == gid:
                        patch.remove()
            if kind in ["any", "arrow"]:
                for patch in self.arrows:
                    if patch.obj_name == gid:
                        patch.remove()

    def plot_1d_get_line(self, gid: str):
        """Get line."""
        for line in self.ax.get_lines():
            _gid = line.get_gid()
            if gid == _gid:
                return line

    def set_xy_line_limits(
        self, y_lower_start=None, y_upper_multiplier=1.1, reset_x: bool = False, reset_y: bool = False
    ):
        """Get x/y-axis limits based on what is plotted."""
        xlimits, ylimits = [], []
        for line in self.ax.get_lines():
            xy = line.get_xydata()
            xlimits.extend([xy[:, 0].min(), xy[:, 0].max()])
            ylimits.extend([xy[:, 1].min(), xy[:, 1].max()])

        if len(xlimits) >= 2 and len(ylimits) >= 2:
            xlimits, ylimits, extent = self._compute_xy_limits(xlimits, ylimits, y_lower_start, y_upper_multiplier)

            # update plot limits
            self.update_extents([extent])
            self.store_plot_limits([extent], [self.ax])

            # reset x-axis range
            if reset_x:
                self.on_zoom_x_axis(*xlimits)
            if reset_y:
                self.on_zoom_y_axis(*ylimits)

    def plot_scatter(
        self,
        x: np.ndarray,
        y: np.ndarray,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        label: str = "",
        y_lower_start=None,
        y_upper_multiplier=1.1,
        gid=PlotIds.PLOT_1D_LINE_GID,
        color="k",
        zorder: int = 5,
        # line_width: int = 1,
        # line_alpha: float = 1.0,
        # line_style: str = "solid",
        **kwargs,
    ):
        """Standard 1d plot."""
        xlimits, ylimits, extent = self._compute_xy_limits(x, y, y_lower_start, y_upper_multiplier)

        # add 1d plot
        self.ax.scatter(
            x,
            y,
            color=color,
            label=label,
            gid=gid,
            zorder=zorder,
            marker=kwargs.get("marker", "o"),
            s=kwargs.get("size", 5),
        )
        if kwargs.get("spectrum_line_fill_under", False):
            self.plot_1d_add_under_curve(x, y, **kwargs)

        # setup axis formatters
        self.ax.yaxis.set_major_formatter(get_intensity_formatter())
        self.set_plot_xlabel(x_label, **kwargs)
        self.set_plot_ylabel(y_label, **kwargs)
        self.set_plot_title(title, **kwargs)
        if kwargs.get("update_limits", True):
            self.ax.set_xlim(xlimits)
            self.ax.set_ylim(ylimits)
            self.store_plot_limits([extent], [self.ax])

            self.setup_new_zoom(
                [self.ax],
                data_limits=[extent],
                allow_extraction=kwargs.get("allow_extraction", True),
                callbacks=kwargs.get("callbacks", {}),
            )

        # Setup X-axis getter
        self.PLOT_TYPE = "scatter"


def get_extent(ax):
    """Get extent."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    return x0, y0, x1, y1
