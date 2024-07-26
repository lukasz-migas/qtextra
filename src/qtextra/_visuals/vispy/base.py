"""Base viewer."""

from __future__ import annotations

import typing as ty

import numpy as np
from koyo.utilities import get_min_max
from vispy.scene import AxisWidget, InfiniteLine, SceneCanvas, ViewBox
from vispy.scene.visuals import Line as LineNode
from vispy.scene.visuals import Markers as MarkersNode
from vispy.util import keys

from qtextra._visuals.vispy.camera import BoxZoomCameraMixin
from qtextra._visuals.vispy.models.extents import Extents
from qtextra.utils.color import hex_to_rgb


class BasePlot(SceneCanvas, BoxZoomCameraMixin):
    """Base view."""

    camera_kwargs: ty.ClassVar[dict[str, ty.Any]] = {"color": (0.0, 0.0, 0.0, 0.3), "border_color": "black"}
    view_kwargs: ty.ClassVar[dict[str, ty.Any]] = {"row": 0, "col": 1}

    def __init__(self, parent, facecolor: str = "black", x_label: str = "", y_label: str = "", **kwargs):
        # setup canvas
        SceneCanvas.__init__(self, keys="interactive", parent=parent, decorate=False)
        self.unfreeze()
        self._send_hover_events = True  # temporary workaround
        self.node = None
        self.nodes = {}
        self.rois = []

        self.grid = self.central_widget.add_grid(spacing=0, bgcolor=facecolor)
        self.view: ViewBox = self.grid.add_view(**self.view_kwargs)
        self._extents = Extents()
        self._kwargs = {"facecolor": facecolor, "x_label": x_label, "y_label": y_label}

        # setup camera
        BoxZoomCameraMixin.__init__(self, **self.camera_kwargs)

        # set callbacks AFTER initializing camera
        self.callbacks = kwargs.pop("callbacks", {})
        self._kwargs.update(**kwargs)

        # connect events
        self.events.mouse_double_click.connect(self._on_mouse_double_click)
        self.events.key_press.connect(self._on_key_press)
        self.events.key_release.connect(self._on_key_release)

        # connect keybinding
        self._key_control = False
        self._key_shift = False
        self._key_alt = False

    def savefig(self, path, dpi: int = 150, transparent: bool = True, **kwargs):
        """Export figure."""
        from imageio import imwrite

        im_array = self.render()
        imwrite(
            path,
            im_array,
            dpi=(dpi, dpi),
            #                 transparency=transparent
        )

        # TODO: add option to resize the plot area
        # if not hasattr(self, "plot_base"):
        #     logger.warning("Cannot save a plot that has not been plotted yet")
        #     return
        # self.figure.savefig(
        #     path,
        #     transparent=transparent,
        #     dpi=dpi,
        #     compression=compression,
        #     format=image_fmt,
        #     optimize=True,
        #     quality=95,
        #     bbox_inches="tight" if tight else None,
        # )

    def on_key_press(self, event):
        """Process key press."""

    @property
    def plot_base(self):
        """Plot base."""
        return self.node

    @property
    def zoom(self):
        """Plot base."""
        return self.view.camera

    @property
    def callbacks(self):
        """Get callbacks."""
        return self.view.camera.callbacks

    @callbacks.setter
    def callbacks(self, value):
        self.view.camera.callbacks = value

    @property
    def camera(self):
        """Get camera."""
        return self.view.camera

    def _on_key_press(self, event):
        """Process keyboard press."""
        self._key_control = keys.CONTROL in event.modifiers
        self._key_shift = keys.SHIFT in event.modifiers
        self._key_alt = keys.ALT in event.modifiers

    #         self.camera.set_keys(key_x=event.key.name=="X", key_y=event.key.name=="Y")
    # print(f"CTRL-{self._key_control}; SHIFT-{self._key_shift}; ALT-{self._key_alt}")

    def _on_key_release(self, event):
        """Process keyboard press."""
        self._key_control = keys.CONTROL in event.modifiers
        self._key_shift = keys.SHIFT in event.modifiers
        self._key_alt = keys.ALT in event.modifiers

    #         self.camera.set_keys(key_x=event.key.name=="X", key_y=event.key.name=="Y")
    # print(f"CTRL-{self._key_control}; SHIFT-{self._key_shift}; ALT-{self._key_alt}")

    def _set_xy_limits_from_array(self, x: np.ndarray, y: np.ndarray, reset: bool = False):
        """Set x/y-axis limits."""
        if reset:
            self._extents.reset()
        xmin, xmax = get_min_max(x)
        ymin, ymax = get_min_max(y)
        self._extents.add_range(xmin, xmax, ymin, ymax)
        self.set_xy_view(*self._extents.get_xy())

    def _set_xy_limits(
        self, x_min: float, x_max: float, y_min: float, y_max: float, x_pad: float = 0, y_pad: float = 0
    ):
        """Sey x/y-axis limits."""
        x_min, x_max, y_min, y_max = x_min - x_pad, x_max + x_pad, y_min - y_pad, y_max + y_pad
        self._extents.add_range(x_min, x_max, y_min, y_max)
        self.set_xy_view(*self._extents.get_xy())

    def on_reset_zoom(self):
        """Reset zoom."""
        print("on_reset_zoom")

    def copy_to_clipboard(self):
        """Copy to clipboard."""
        print("copy_to_clipboard")
        return None

    def set_xy_view(self, x_min: float, x_max: float, y_min: float, y_max: float):
        """Set x/y limits."""
        self.view.camera.simple_zoom(x_min, x_max, y_min, y_max)
        self.view.camera.set_extents(x_min, x_max, y_min, y_max)
        self.view.camera.set_default_state()

    def on_zoom_x_axis(self, x_min: float, x_max: float):
        y_min, y_max = self._extents.get_y()
        self.view.camera.simple_zoom(x_min, x_max, y_min, y_max)

    def on_set_x_axis(self, x_min: float, x_max: float):
        pass

    def on_zoom_xy_axis(self, start_x: float, end_x: float, start_y: float, end_y: float):
        """Horizontal and vertical zoom."""
        self.view.camera.simple_zoom(start_x, end_x, start_y, end_y)

    def get_xy_limits(self) -> tuple[float, float, float, float]:
        """Get x/y-axis limits."""
        return self._extents.get_xy()

    def get_xy_zoom(self) -> tuple[float, float, float, float]:
        """Get current zoom level."""
        return self.camera.extent

    def plot_remove_patches(self):
        pass

    def plot_add_patch(self, *args, **kwargs):
        pass

    def set_xy_line_limits(self, *args, **kwargs):
        pass

    def get_existing_patch(self, *args, **kwargs):
        return None

    def repaint(self, repaint: bool = True):
        """Repaint."""
        self.update()

    def clear(self):
        """Clear plot."""
        self._extents.reset()
        if self.node is not None:
            self.node.parent = None
            self.node = None
        for value in self.nodes.values():
            del value
        self.nodes.clear()


class PlotLine(BasePlot):
    """Line view."""

    camera_kwargs: ty.ClassVar[dict[str, ty.Any]] = {
        "color": (0.0, 0.0, 0.0, 0.3),
        "border_color": "black",
        "is_1d": True,
    }
    x_axis, y_axis = None, None

    def __init__(self, parent, facecolor="white", x_label: str = "", y_label: str = "", **kwargs):
        super().__init__(parent, facecolor=facecolor, x_label=x_label, y_label=y_label, **kwargs)
        self.unfreeze()

    def init(self):
        """Initialize view."""
        self.node: LineNode = LineNode(color=(0, 0, 0), parent=self.view.scene, method="gl")
        self.set_axes(
            "#000000" if self._kwargs["facecolor"] in ["white", "#FFFFFF"] else "#FFFFFF",
            x_label=self._kwargs["x_label"],
            y_label=self._kwargs["y_label"],
        )

    # noinspection PyTypeChecker
    def set_axes(
        self,
        label_color: str = "#000000",
        x_label: str = "",
        y_label: str = "",
        font_size: int = 10,
        axis_label_margin: int = 50,
    ):
        """Set x/y-axis of the plot."""
        # set x-axis
        self.x_axis = AxisWidget(
            orientation="bottom",
            axis_label=x_label,
            axis_font_size=font_size,
            axis_label_margin=axis_label_margin,
            tick_label_margin=20,
            axis_color=label_color,
            text_color=label_color,
        )
        self.x_axis.height_max = 80
        self.grid.add_widget(self.x_axis, row=1, col=1)

        self.y_axis = AxisWidget(
            axis_label=y_label,
            axis_font_size=font_size,
            axis_label_margin=axis_label_margin,
            tick_label_margin=10,
            axis_color=label_color,
            text_color=label_color,
        )
        self.y_axis.width_max = 80
        self.grid.add_widget(self.y_axis, row=0, col=0)

        self.x_axis.link_view(self.view)
        self.y_axis.link_view(self.view)

    def plot_1d(
        self,
        x,
        y,
        color=(0, 0, 0),
        width: int = 5,
        gid: str = "line",
        **kwargs,
    ):
        """Plot."""
        if self.node is None:
            self.init()
        self.node.set_data(np.c_[x, y], color=color, width=width)
        self.node.order = kwargs.pop("zorder", 0)
        self.nodes[gid] = self.node
        self._set_xy_limits_from_array(x, y)

    def plot_1d_update_data(
        self,
        x,
        y,
        line_width: int = 1,
        color: str = "#000000",
        gid: str = "line",
        **kwargs,
    ):
        """Update plot data."""
        if self.node is None:
            self.init()
        self.node.set_data(np.c_[x, y], width=line_width, color=color)
        self.node.order = kwargs.pop("zorder", 0)
        self.nodes[gid] = self.node
        self._set_xy_limits_from_array(x, y)

    def plot_1d_add(self, x: np.ndarray, y: np.ndarray, color=(0, 1, 0), width: int = 1, gid: str = "line", zorder=0):
        """Add new node."""
        if gid in self.nodes:
            node = self.nodes[gid]
        else:
            node: LineNode = LineNode(color=color, parent=self.view.scene)
        node.order = zorder
        node.set_data(np.c_[x, y], color=color, width=width)
        self.nodes[gid] = node
        self._set_xy_limits_from_array(x, y)

    def plot_1d_remove(self, gid: str | None = None):
        """Remove line."""
        if gid is None:
            self.node.set_data([])
        else:
            try:
                self.nodes[gid].parent = None
                del self.nodes[gid]
            except KeyError:
                print(f"Could not remove line node {gid}")

    def plot_1d_update_color(self, color, gid: str | None = None):
        """Update line color."""
        if gid is None:
            self.node.set_data(color=color)
        else:
            self.nodes[gid].set_data(color=color)

    def plot_1d_update_line_width(self, line_width: float, gid: str | None = None):
        """Update line width."""
        if gid is None:
            self.node.set_data(width=line_width)
        else:
            self.nodes[gid].set_data(width=line_width)

    def plot_1d_update_line_style(self, line_style: str, gid: str | None = None):
        """Update plot style."""
        print("Not supported!")

    def plot_1d_update_line_alpha(self, opacity: float, gid: str | None = None):
        """Update line transparency."""
        print(self.node.color, opacity, gid)
        # if gid is None:
        #     self.node.set_data(width=line_width)
        # else:
        #     self.nodes[gid].set_data(width=line_width)

    def plot_1d_centroid(self, *args, **kwargs):
        pass

    def plot_add_vline(
        self,
        xpos: float = 0,
        ymin: float = 0,
        ymax: float = 1,
        color: str = "#000000",
        alpha: float = 1.0,
        gid: str = "vline",
    ):
        """Add vertical line."""
        if isinstance(color, str):
            color = hex_to_rgb(color, alpha=alpha * 255)
        node: InfiniteLine = InfiniteLine(xpos, parent=self.view.scene, vertical=True, color=color)
        self.nodes[gid] = node

    def plot_add_hline(
        self,
        ypos: float = 0,
        xmin: float = 0,
        xmax: float = 1,
        color: str = "#000000",
        alpha: float = 1.0,
        gid: str = "hline",
    ):
        """Add horizontal line."""
        if isinstance(color, str):
            color = hex_to_rgb(color, alpha=alpha * 255)
        node: InfiniteLine = InfiniteLine(ypos, parent=self.view.scene, vertical=False, color=color)
        node.order = 100
        self.nodes[gid] = node

    def plot_remove_line(self, gid: str):
        """Remove line from the scene."""
        try:
            self.nodes[gid].parent = None
            del self.nodes[gid]
        except KeyError:
            pass


class PlotScatter(PlotLine):
    """Scatter view."""

    camera_kwargs: ty.ClassVar[dict[str, ty.Any]] = {
        "color": (0.0, 0.0, 0.0, 0.3),
        "border_color": "black",
        "is_1d": False,
    }

    def __init__(self, parent, facecolor="white", x_label: str = "", y_label: str = "", **kwargs):
        super().__init__(parent, facecolor=facecolor, x_label=x_label, y_label=y_label, **kwargs)
        self.unfreeze()

    def init(self):
        """Initialize view."""
        self.node: MarkersNode = MarkersNode(parent=self.view.scene)

        self.set_axes(
            "#000000" if self._kwargs["facecolor"] in ["white", "#FFFFFF"] else "#FFFFFF",
            x_label=self._kwargs["x_label"],
            y_label=self._kwargs["y_label"],
        )

    def plot_scatter(
        self,
        x,
        y,
        face_color: str = "#FF0000",
        edge_color: str = "#FF0000",
        zorder: int = 5,
        size: float | np.ndarray = 1,
        **kwargs,
    ):
        if self.node is None:
            self.init()

        self.node.order = zorder
        self.node.set_data(
            np.c_[x, y],
            symbol="square",
            size=size,
            face_color=face_color,
            edge_color=edge_color,
            scaling=False,
        )
        self._set_xy_limits_from_array(x, y, True)

    def update_scatter(
        self,
        x,
        y,
        face_color: str = "#FF0000",
        edge_color: str = "#FF0000",
        zorder: int = 5,
        size: float | np.ndarray = 2,
        **kwargs,
    ):
        """Update scatter data."""
        self.node.order = zorder
        self.node.set_data(
            np.c_[x, y],
            symbol="square",
            size=size,
            face_color=face_color,
            edge_color=edge_color,
            edge_width=0,
            scaling=False,
        )
        # self._set_xy_limits_from_array(x, y, True)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QDialog, QVBoxLayout

    from qtextra.utils.dev import qapplication

    # def fcn():
    #     global image
    #     image += int(np.random.randint(0, 20, 1))
    #     # image = np.random.randint(0, 255, (N_PTS, N_PTS), dtype=np.ubyte)
    #     view_image.plot_2d_update_data(image)
    #
    # def set_opacity_1():
    #     view_image.node.opacity = slider1.value() / 100
    #
    # def set_opacity_2():
    #     view_image.mask_node.clim = (slider2.value(), 255)
    #     # view_image.mask_node.opacity = slider2.value() / 100
    #
    # def set_width():
    #     view_image.mask_node.clim = (slider2.value(), slider3.value())
    #
    # def set_units():
    #     view_image.add_scalebar(show=True, units="px" if not checkbox1.isChecked() else "um", px_size=10)
    #     view_image.grid_node.visible = checkbox1.isChecked()

    _ = qapplication()  # analysis:ignore

    # view_image = PlotHeatmap(None)

    dlg = QDialog()

    # slider1 = make_labelled_slider(dlg)
    # slider1.valueChanged.connect(set_opacity_1)
    # slider2 = make_labelled_slider(dlg, max_val=255)
    # slider2.valueChanged.connect(set_opacity_2)
    # slider3 = make_labelled_slider(dlg)
    # slider3.valueChanged.connect(set_width)
    # checkbox1 = make_checkbox(dlg, "Microns")
    # checkbox1.stateChanged.connect(set_units)

    layout = QVBoxLayout()
    # layout.addWidget(view_line.native)
    # layout.addWidget(slider1)
    # layout.addWidget(slider2)
    # layout.addWidget(slider3)
    # layout.addWidget(checkbox1)
    dlg.setLayout(layout)

    N_PTS = 100
    # view_line.plot_1d(np.arange(N_PTS), np.random.randint(-255, 255, N_PTS), color=(0, 1, 0))
    # view_line.add_line(np.arange(N_PTS), np.random.randint(0, 255, N_PTS), color=(1, 0, 0))
    # view_line.add_line(np.arange(N_PTS), np.random.randint(0, 255, N_PTS), color=(0, 0, 1))
    # view_line.plot_add_hline(color="#FFFFFF")
    # view_line.plot_add_vline(color="#FFFFFF")
    # view_line.plot_scatter(np.arange(N_PTS), np.arange(N_PTS))

    # generate random image
    # image = np.random.normal(size=(100, 100, 3))
    # image[20:80, 20:80] += 3.0
    # image[50] += 3.0
    # image[:, 50] += 3.0
    # image = ((image - image.min()) * (253.0 / (image.max() - image.min()))).astype(np.ubyte)
    # print(image)
    image = np.random.randint(0, 255, (N_PTS, N_PTS), dtype=np.ubyte)
    # image = np.zeros((N_PTS, N_PTS), dtype=np.ubyte)
    # image[0:500, 0:500] = 150
    # view_image.plot_2d(image, opacity=0.5)
    # view_image.add_roi("rect", [0, 500, 0, 500])
    # view_image.add_roi("poly", [[50, 1500], [100, 1523], [0, 500], [50, 1500]])
    # view_image.add_roi("circle", [(500, 500), 100, 1000])

    # cmap = make_listed_colormap(["#FF0000", "#FF00FF"], True)
    # N_PTS += 100
    # image = np.zeros((N_PTS, N_PTS), dtype=np.ubyte)
    # image[500:600, 0:500] = 127
    # image[500:600, 500:] = 255
    # view_image.plot_2d_mask(image, opacity=0.5, colormap=cmap)

    # view_image.plot_2d_mask(np.random.randint(0, 255, (N_PTS, N_PTS), dtype=np.ubyte), colormap=cmap)

    # timer = QTimer(dlg)
    # timer.setInterval(20)
    # timer.timeout.connect(fcn)
    # timer.start()

    dlg.show()
    # view_line.show()
    # view_image.show()
    sys.exit(dlg.exec_())
    # run()
