"""Qt widget that embeds the canvas."""

from typing import TYPE_CHECKING

from napari._qt.containers.qt_layer_list import QtLayerList
from napari._vispy.utils.visual import create_vispy_layer
from napari.utils._proxies import ReadOnlyWrapper
from napari_plot._vispy.camera import VispyCamera
from napari_plot._vispy.overlays.axis import VispyXAxisVisual, VispyYAxisVisual
from napari_plot._vispy.tools.drag import VispyDragTool
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout

from qtextra._napari.common.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from qtextra._napari.common.qt_viewer import QtViewerBase
from qtextra._napari.line._vispy.canvas import VispyCanvas
from qtextra._napari.line.component_controls.qt_view_toolbar import QtViewLeftToolbar, QtViewRightToolbar
from qtextra._napari.line.layer_controls.qt_layer_buttons import QtLayerButtons, QtViewerButtons
from qtextra.config.theme import CANVAS

if TYPE_CHECKING:
    from napari_plot.viewer import ViewerModel


class QtViewer(QtViewerBase):
    """Qt view for the napari Viewer model."""

    def __init__(
        self,
        view,
        viewer: "ViewerModel",
        parent=None,
        disable_controls: bool = False,
        add_toolbars: bool = True,
        allow_extraction: bool = True,
        allow_tools: bool = False,
        connect_theme: bool = True,
    ):
        super().__init__(
            view,
            viewer,
            parent=parent,
            disable_controls=disable_controls,
            add_toolbars=add_toolbars,
            allow_extraction=allow_extraction,
            allow_tools=allow_tools,
        )

        if connect_theme:
            CANVAS.evt_theme_changed.connect(self.toggle_theme)
            self.toggle_theme()  # force theme change

    def toggle_theme(self, _=None):
        """Update theme."""
        self.canvas.bgcolor = CANVAS.as_array("canvas")
        self.viewer.axis.label_color = CANVAS.as_array("axis")
        self.viewer.axis.tick_color = CANVAS.as_array("axis")
        self.viewer.text_overlay.color = CANVAS.as_array("label")

    def on_resize(self, event):
        """Update cached x-axis offset."""
        self.viewer._canvas_size = tuple(self.canvas.size[::-1])

    def _post_init(self):
        """Setup after full-initialization."""
        self.viewer_left_toolbar.connect_toolbar()
        self.viewer_right_toolbar.connect_toolbar()

    def _create_widgets(self, **kwargs):
        """Create ui widgets."""
        # widget showing layer controls
        self.controls = QtLayerControlsContainer(self.viewer)
        # widget showing current layers
        self.layers = QtLayerList(self.viewer.layers)
        # widget showing layer buttons (e.g. add new shape)
        self.layerButtons = QtLayerButtons(self.viewer)
        # viewer buttons to control 2d/3d, grid, transpose, etc
        self.viewerButtons = QtViewerButtons(self.viewer, self)
        # toolbar
        self.viewer_left_toolbar = QtViewLeftToolbar(self.view, self.viewer, self, **kwargs)
        self.viewer_right_toolbar = QtViewRightToolbar(self.view, self.viewer, self, **kwargs)

    def _set_layout(self, add_toolbars: bool, **kwargs):
        # set in main canvas
        # main_widget = QWidget()
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.canvas.native, stretch=True)
        image_layout.setContentsMargins(0, 2, 0, 2)

        # view widget
        main_layout = QHBoxLayout()
        main_layout.setSpacing(1)
        main_layout.addLayout(image_layout)
        main_layout.setContentsMargins(2, 2, 2, 2)
        if add_toolbars:
            main_layout.insertWidget(0, self.viewer_left_toolbar)
            main_layout.addWidget(self.viewer_right_toolbar)
        else:
            self.viewer_left_toolbar.setVisible(False)
            self.viewer_right_toolbar.setVisible(False)
            main_layout.setSpacing(0)
        self.setLayout(main_layout)

    def _create_canvas(self) -> None:
        """Create the canvas and hook up events."""
        self.canvas = VispyCanvas(
            keys=None,
            vsync=True,
            parent=self,
            size=self.viewer._canvas_size[::-1],
        )
        self.canvas.events.reset_view.connect(self.viewer.reset_view)
        self.canvas.events.reset_x.connect(self.viewer.reset_x_view)
        self.canvas.events.reset_y.connect(self.viewer.reset_y_view)

        self.canvas.connect(self.on_mouse_move)
        self.canvas.connect(self.on_mouse_press)
        self.canvas.connect(self.on_mouse_release)
        self.canvas.connect(self._key_map_handler.on_key_press)
        self.canvas.connect(self._key_map_handler.on_key_release)
        self.canvas.connect(self.on_mouse_wheel)
        self.canvas.connect(self.on_draw)
        self.canvas.connect(self.on_resize)

    def _set_events(self):
        # bind events
        self.viewer.layers.selection.events.active.connect(self._on_active_change)
        self.viewer.camera.events.mouse_pan.connect(self._on_mouse_pan)
        self.viewer.camera.events.mouse_zoom.connect(self._on_mouse_zoom)
        self.viewer.cursor.events.style.connect(self._on_cursor)
        self.viewer.cursor.events.size.connect(self._on_cursor)
        self.viewer.layers.events.reordered.connect(self._reorder_layers)
        self.viewer.layers.events.inserted.connect(self._on_add_layer_change)
        self.viewer.layers.events.removed.connect(self._remove_layer)

    def _set_view(self):
        """Set view."""
        self.grid = self.canvas.central_widget.add_grid(spacing=0)
        self.view = self.grid.add_view(row=1, col=1)
        # this gives small padding to the right of the plot
        self.padding_x = self.grid.add_widget(row=0, col=2)
        self.padding_x.width_max = 20
        # this gives small padding to the top of the plot
        self.padding_y = self.grid.add_widget(row=0, col=0, col_span=2)
        self.padding_y.height_max = 20
        with self.canvas.modify_context() as canvas:
            canvas.grid = self.grid
            canvas.view = self.view

    def _set_camera(self):
        self.camera = VispyCamera(self.view, self.viewer.camera, self.viewer)
        self.canvas.connect(self.camera.on_draw)
        # self.camera.camera.events.box_press.connect(self._on_boxzoom)
        # self.camera.camera.events.box_move.connect(self._on_boxzoom_move)

    def _on_boxzoom(self, event):
        """Update boxzoom visibility."""
        self.viewer.span.visible = event.visible
        if not event.visible:
            self.viewer.span.position = 0, 0
        # self.viewer.boxzoom.visible = event.visible
        # if not event.visible:  # reset so next time its displayed it will be not visible to the user
        #     self.viewer.boxzoom.rect = 0, 0, 0, 0

    def _on_boxzoom_move(self, event):
        """Update boxzoom."""
        rect = event.rect
        self.viewer.span.position = rect[0], rect[1]

    def _add_visuals(self) -> None:
        """Add visuals for axes, scale bar."""
        for layer in self.viewer.layers:
            self._add_layer(layer)
        for overlay in self.viewer._overlays.values():
            self._add_overlay(overlay)

        # add span
        self.tool = VispyDragTool(self.viewer, view=self.view, order=1e5)

        # add gridlines
        # self.grid_lines = VispyGridLinesOverlay(self.viewer, parent=self.view, order=1e6)
        #
        # add x-axis widget
        self.x_axis = VispyXAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.x_axis.node, row=2, col=1)
        self.x_axis.node.link_view(self.view)
        self.x_axis.node.height_max = self.viewer.axis.x_max_size
        self.x_axis.interactive = True

        # add y-axis widget
        self.y_axis = VispyYAxisVisual(self.viewer, parent=self.view, order=1e6 + 1)
        self.grid.add_widget(self.y_axis.node, row=1, col=0)
        self.y_axis.node.link_view(self.view)
        self.y_axis.node.width_max = self.viewer.axis.y_max_size
        self.y_axis.interactive = True

        # # add label
        # self.text_overlay = VispyTextOverlay(self, self.viewer, parent=self.view, order=1e6 + 2)

        # add box zoom visual
        # self.boxzoom = VispyBoxZoomVisual(self.viewer, self.camera.camera, parent=self.view)

        with self.canvas.modify_context() as canvas:
            canvas.x_axis = self.x_axis
            canvas.y_axis = self.y_axis

    def _add_layer(self, layer):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        layer : napari.layers.Layer
            Layer to be added.
        """
        vispy_layer = create_vispy_layer(layer)
        vispy_layer.node.parent = self.view.scene
        vispy_layer.order = len(self.viewer.layers) - 1
        self.layer_to_visual[layer] = vispy_layer

    def on_open_controls_dialog(self, event=None):
        """Open dialog responsible for layer settings."""
        from qtextra._napari.line.component_controls.qt_layers_dialog import DialogLineControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = DialogLineControls(self)
        # make sure the dialog is shown
        self._layers_controls_dialog.show()
        # make sure the the dialog gets focus
        self._layers_controls_dialog.raise_()  # for macOS
        self._layers_controls_dialog.activateWindow()  # for Windows

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        CANVAS.evt_theme_changed.disconnect(self.toggle_theme)
        self.canvas.native.deleteLater()
        event.accept()

    def _map_canvas2world(self, position):
        """Map position from canvas pixels into world coordinates.

        Parameters
        ----------
        position : 2-tuple
            Position in canvas (x, y).

        Returns
        -------
        coords : tuple
            Position in world coordinates, matches the total dimensionality
            of the viewer.
        """
        position = list(position)
        position[0] -= self.view.pos[0]
        position[1] -= self.view.pos[1]
        transform = self.view.camera.transform.inverse
        mapped_position = transform.map(position)[:2]
        position_world_slice = mapped_position[::-1]

        position_world = [0, 0]
        for i, d in enumerate((0, 1)):
            position_world[d] = position_world_slice[i]
        return tuple(position_world)

    def on_draw(self, _event):
        """Called whenever the canvas is drawn.

        This is triggered from vispy whenever new data is sent to the canvas or
        the camera is moved and is connected in the `QtViewer`.
        """
        for layer in self.viewer.layers:
            if layer.ndim <= 2:
                layer._update_draw(
                    scale_factor=1 / self.viewer.camera.zoom,
                    corner_pixels_displayed=self._canvas_corners_in_world[:, -layer.ndim :],
                    shape_threshold=self.canvas.size,
                )

    def _process_mouse_event(self, mouse_callbacks, event):
        """Called whenever mouse pressed in canvas.

        Parameters
        ----------
        mouse_callbacks : function
            Mouse callbacks function.
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        if event.pos is None:
            return

        # Add the view ray to the event
        event.view_direction = None  # always None because we will display 2d data
        event.up_direction = None  # always None because we will display 2d data

        # Update the cursor position
        self.viewer.cursor.position = self._map_canvas2world(event.pos)

        # Add the cursor position to the event
        event.position = self.viewer.cursor.position

        # Add the displayed dimensions to the event
        event.dims_displayed = [0, 1]

        # Put a read only wrapper on the event
        event = ReadOnlyWrapper(event)
        mouse_callbacks(self.viewer, event)

        layer = self.viewer.layers.selection.active
        if layer is not None:
            mouse_callbacks(layer, event)
