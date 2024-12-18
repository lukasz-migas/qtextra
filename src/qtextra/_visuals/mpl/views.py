"""MPL based views."""

from __future__ import annotations

import typing as ty

import numpy as np
from koyo.secret import get_short_hash
from qtpy.QtCore import QMutexLocker
from qtpy.QtWidgets import QWidget

from qtextra._visuals.mpl.plot_base import PlotBase
from qtextra._visuals.views_base import MUTEX, ViewBase

if ty.TYPE_CHECKING:
    import pandas as pd


class ViewMplLine(ViewBase):
    """View."""

    PLOT_TYPE = "line"

    def __init__(self, parent: QWidget, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(parent, *args, **kwargs)
        self.PLOT_ID = get_short_hash()
        self.figure = PlotBase(parent, *args, main_parent=self.main_parent, **kwargs)
        self.figure.evt_unregister.connect(self.unregister)

    @property
    def widget(self) -> PlotBase:
        """Get widget."""
        return self.figure

    def plot(
        self, x: np.ndarray, y: np.ndarray, repaint: bool = True, forced_kwargs: dict | None = None, **kwargs: ty.Any
    ) -> None:
        """Simple line plot."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)

            try:
                self.update(x, y, repaint=repaint, **kwargs)
            except (ValueError, AttributeError, OverflowError):
                self.figure.clear()
                self.figure.plot_1d(
                    x, y, x_label=self.x_label, y_label=self.y_label, callbacks=self._callbacks, **kwargs
                )
                self.figure.repaint(repaint)

                # set data
                self._data.update(x=x, y=y)

    def scatter(
        self,
        x: np.ndarray,
        y: np.ndarray,
        marker: str | np.ndarray = "o",
        color: str | np.ndarray = "k",
        size: float = 5,
        repaint: bool = True,
        **kwargs: ty.Any,
    ):
        """Simple scatter plot."""
        with QMutexLocker(MUTEX):
            self.figure.plot_scatter(
                x,
                y,
                marker=marker,
                color=color,
                x_label=self.x_label,
                y_label=self.y_label,
                callbacks=self._callbacks,
                size=size,
                **kwargs,
            )
            self.figure.repaint(repaint)

    def update(self, x: np.ndarray, y: np.ndarray, repaint: bool = True, **kwargs: ty.Any) -> None:
        """Update plot without having to clear it."""
        #         t_start = time.time()
        self.set_labels(**kwargs)

        # update plot
        self.figure.plot_1d_update_data(x, y, self.x_label, self.y_label, **kwargs)
        self.figure.set_xy_line_limits(reset_y=True)
        # self.figure.on_reset_zoom(False)
        self.figure.repaint(repaint)

        # set data
        self._data.update(x=x, y=y)

    def update_x(self, x: np.ndarray, repaint: bool = True, **kwargs: ty.Any) -> None:
        """Update x-axis."""
        with QMutexLocker(MUTEX):
            self.set_labels(**kwargs)

            # update plot
            self.figure.plot_1d_update_x_axis(x, **kwargs)
            self.figure.set_xy_line_limits(reset_x=True)
            self.figure.repaint(repaint)

    def reset(self) -> None:
        """Resets the image."""
        self.light_clear()

        if "x" not in self._data or "y" not in self._data:
            return
        # show base image
        self.plot(self._data["x"], self._data["y"], **self._plt_kwargs)

    def figure_update(self, add_zoom: bool = True, repaint: bool = True, tight: bool = True):
        """Update and repaint figure."""
        with QMutexLocker(MUTEX):
            self.figure.tight(tight)
            if add_zoom:
                self.figure.add_zoom()
            self.figure.repaint(repaint)

    def plot_confusion_matrix(
        self,
        matrix: np.ndarray,
        labels: list[str],
        which: str = "counts",
        repaint: bool = True,
        tight: bool = True,
        **kwargs,
    ):
        """Plot confusion matrix."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_confusion_matrix(matrix, labels=labels, which=which, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def plot_roc(
        self,
        fpr: dict[str, np.ndarray],
        tpr: dict[str, np.ndarray],
        labels: dict[str, np.ndarray],
        plot_micro: bool = True,
        plot_macro: bool = True,
        repaint: bool = True,
        tight: bool = True,
        **kwargs,
    ):
        """Plot confusion matrix."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_roc(fpr, tpr, labels, plot_micro=plot_micro, plot_macro=plot_macro, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def plot_precision_recall(
        self,
        precision: dict[str, np.ndarray],
        recall: dict[str, np.ndarray],
        labels: dict[str, np.ndarray],
        plot_micro: bool = True,
        repaint: bool = True,
        tight: bool = True,
        **kwargs,
    ):
        """Plot confusion matrix."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_precision_recall(precision, recall, labels, plot_micro=plot_micro, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def plot_precision_recall_f1_support(
        self,
        scores: dict[str, np.ndarray],
        labels: list[str],
        repaint: bool = True,
        tight: bool = True,
        **kwargs,
    ):
        """Plot confusion matrix."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_precision_recall_fscore_support(scores, labels, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def plot_violin(self, df: pd.DataFrame, repaint: bool = True, tight: bool = True, **kwargs):
        """Plot violin plot."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_violin(df, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def plot_boxplot(self, df: pd.DataFrame, repaint: bool = True, tight: bool = True, **kwargs):
        """Plot violin plot."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_boxplot(df, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def plot_boxenplot(self, df: pd.DataFrame, repaint: bool = True, tight: bool = True, **kwargs):
        """Plot violin plot."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_boxenplot(df, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def plot_stripplot(self, df: pd.DataFrame, repaint: bool = True, tight: bool = True, **kwargs):
        """Plot strip plot."""
        with QMutexLocker(MUTEX):
            self.figure.clear()
            self.figure.plot_stripplot(df, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def set_title(self, title, repaint: bool = True, tight: bool = True, **kwargs):
        """Set title on the plot."""
        with QMutexLocker(MUTEX):
            self.figure.set_plot_title(title, **kwargs)
            self.figure.tight(tight)
            self.figure.repaint(repaint)

    def add_line(self, x, y, color: str = "r", gid: str = "gid", zorder: int = 5, repaint: bool = True):
        """Add line."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_add(x, y, color, gid, zorder=zorder)
            self.figure.set_xy_line_limits()
            self.figure.repaint(repaint)

    def add_centroids(self, x: np.ndarray, y: np.ndarray, gid: str, repaint: bool = True):
        """Add centroid."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_centroid(x, y, gid=gid)
            self.figure.repaint(repaint)

    def remove_gid(self, gid: str, repaint: bool = True):
        """Remove gid."""
        with QMutexLocker(MUTEX):
            self.figure.remove_gid(gid)
            self.figure.repaint(repaint)

    def remove_line(self, gid: str, repaint: bool = True):
        """Remove line."""
        with QMutexLocker(MUTEX):
            try:
                self.figure.plot_1d_remove(gid)
                self.figure.set_xy_line_limits()
                self.figure.repaint(repaint)
            except AttributeError:
                pass

    def update_line_color(self, gid: str, color: ty.Union[str, np.ndarray], repaint: bool = True):
        """Update line color."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_color(gid, color)
            self.figure.repaint(repaint)

    def update_line_width(self, width: float = 1.0, gid: ty.Optional[str] = None, repaint: bool = True):
        """Update line width."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_width(width, gid)
            self.figure.repaint(repaint)

    def update_line_style(self, style: str = "solid", gid: ty.Optional[str] = None, repaint: bool = True):
        """Update line style."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_style(style, gid)
            self.figure.repaint(repaint)

    def update_line_alpha(self, alpha: float = 1.0, gid: ty.Optional[str] = None, repaint: bool = True):
        """Update line style."""
        with QMutexLocker(MUTEX):
            self.figure.plot_1d_update_line_alpha(alpha, gid)
            self.figure.repaint(repaint)

    def _update(self):
        """Update plot with current data."""
        with QMutexLocker(MUTEX):
            self.update(self._data["x"], self._data["y"], **self._plt_kwargs)
