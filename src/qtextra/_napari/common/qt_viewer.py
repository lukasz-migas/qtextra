"""Qt widget that embeds the canvas."""
# Third-party imports
from typing import Tuple

import numpy as np
from napari._qt.utils import QImg2array, circle_pixmap, square_pixmap
from napari.utils._proxies import ReadOnlyWrapper
from napari.utils.interactions import (
    mouse_move_callbacks,
    mouse_press_callbacks,
    mouse_release_callbacks,
    mouse_wheel_callbacks,
)
from napari.utils.key_bindings import KeymapHandler
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QCursor, QGuiApplication
from qtpy.QtWidgets import QWidget

from qtextra._napari.common._utilities import crosshair_pixmap
from qtextra._napari.common._vispy.vispy_canvas import VispyCanvas


class QtViewerBase(QWidget):
    """Qt view for the napari Viewer model.

    Parameters
    ----------
    viewer : imimspy.napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    canvas : vispy.scene.SceneCanvas
        Canvas for rendering the current view.
    layer_to_visual : dict
        Dictionary mapping napari layers with their corresponding vispy_layers.
    view : vispy scene widget
        View displayed by vispy canvas. Adds a vispy ViewBox as a child widget.
    viewer :
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, view, viewer, parent=None, disable_controls: bool = False, **kwargs):
        super().__init__(parent=parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(False)
        QCoreApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)

        # handle to the viewer instance
        self.view = view
        self.viewer = viewer

        # keyboard handler
        self._key_map_handler = KeymapHandler()
        self._key_map_handler.keymap_providers = [self.viewer]
        self._key_bindings_dialog = None
        self._disable_controls = disable_controls
        self._layers_controls_dialog = None

        # This dictionary holds the corresponding vispy visual for each layer
        self.layer_to_visual = {}

        self._cursors = {
            "cross": Qt.CrossCursor,
            "forbidden": Qt.ForbiddenCursor,
            "pointing": Qt.PointingHandCursor,
            "horizontal_move": Qt.SizeHorCursor,
            "vertical_move": Qt.SizeVerCursor,
            "standard": QCursor(),
        }

        # create ui widgets
        self._create_widgets(**kwargs)

        # create main vispy canvas
        self._create_canvas()

        # set ui
        self._set_layout(**kwargs)

        # activate layer change
        self._on_active_change()

        # setup events
        self._set_events()

        # add layers
        for layer in self.viewer.layers:
            self._add_layer(layer)

        # setup view
        self._set_view()

        # setup camera
        self._set_camera()

        # Add axes, scalebar, grid and colorbar visuals
        self._add_visuals()

        # add extra initialisation
        self._post_init()

    def __getattr__(self, name):
        return object.__getattribute__(self, name)

    @property
    def pos_offset(self) -> Tuple[int, int]:
        """Window offset."""
        return 0, 0

    def _create_canvas(self) -> None:
        """Create the canvas and hook up events."""
        self.canvas = VispyCanvas(
            keys=None,
            vsync=True,
            parent=self,
            size=self.viewer._canvas_size[::-1],
        )
        self.canvas.events.reset_view.connect(self.viewer.reset_view)
        self.canvas.connect(self.on_mouse_move)
        self.canvas.connect(self.on_mouse_press)
        self.canvas.connect(self.on_mouse_release)
        self.canvas.connect(self._key_map_handler.on_key_press)
        self.canvas.connect(self._key_map_handler.on_key_release)
        self.canvas.connect(self.on_mouse_wheel)
        self.canvas.connect(self.on_draw)
        self.canvas.connect(self.on_resize)

    def _create_widgets(self, **kwargs):
        """Create ui widgets."""
        raise NotImplementedError("Must implement method")

    def _set_layout(self, **kwargs):
        # set in main canvas
        raise NotImplementedError("Must implement method")

    def _set_events(self):
        raise NotImplementedError("Must implement method")

    def _set_camera(self):
        raise NotImplementedError("Must implement method")

    def _add_visuals(self) -> None:
        """Add visuals for axes, scale bar."""
        raise NotImplementedError("Must implement method")

    def _set_view(self):
        """Set view."""
        self.view = self.canvas.central_widget.add_view()

    def _post_init(self):
        """Complete initialization with post-init events."""

    def _constrain_width(self, _event):
        """Allow the layer controls to be wider, only if floated.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        if self.dockLayerControls.isFloating():
            self.controls.setMaximumWidth(700)
        else:
            self.controls.setMaximumWidth(220)

    def _on_active_change(self, _event=None):
        """When active layer changes change keymap handler.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        active_layer = self.viewer.layers.selection.active
        if active_layer in self._key_map_handler.keymap_providers:
            self._key_map_handler.keymap_providers.remove(active_layer)

        if active_layer is not None:
            self._key_map_handler.keymap_providers.insert(0, active_layer)

        # If a QtAboutKeyBindings exists, update its text.
        if self._key_bindings_dialog is not None:
            self._key_bindings_dialog.update_active_layer()

    def _on_add_layer_change(self, event):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        layer = event.value
        self._add_layer(layer)

    def _add_layer(self, layer):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        layer : napari.layers.Layer
            Layer to be added.
        """
        raise NotImplementedError("Must implement method")

    def _remove_layer(self, event):
        """When a layer is removed, remove its parent.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        layer = event.value
        vispy_layer = self.layer_to_visual[layer]
        vispy_layer.close()
        del vispy_layer
        self._reorder_layers(None)

    def _reorder_layers(self, _event):
        """When the list is reordered, propagate changes to draw order.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        for i, layer in enumerate(self.viewer.layers):
            vispy_layer = self.layer_to_visual[layer]
            vispy_layer.order = i
        self.canvas._draw_order.clear()
        self.canvas.update()

    def on_save_figure(self, path=None):
        """Export figure."""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.screenshot, self)
        if dialog.exec_():
            pass

    def screenshot(self, path=None):
        """Take currently displayed screen and convert to an image array.

        Parameters
        ----------
        path : str
            Filename for saving screenshot image.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        from skimage.io import imsave

        img = QImg2array(self.canvas.native.grabFramebuffer())
        if path is not None:
            imsave(path, img)  # scikit-image imsave method
        return img

    def _on_interactive(self, _event):
        """Link interactive attributes of view and viewer.

        Parameters
        ----------
        _event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self.view.interactive = self.viewer.camera.interactive

    def _on_cursor(self, _event=None):
        """Set the appearance of the mouse cursor."""
        cursor = self.viewer.cursor.style
        # Scale size by zoom if needed
        if self.viewer.cursor.scaled:
            size = self.viewer.cursor.size * self.viewer.camera.zoom
        else:
            size = self.viewer.cursor.size

        if cursor == "square":
            # make sure the square fits within the current canvas
            if size < 8 or size > (min(*self.viewer.window._qt_viewer.canvas.size) - 4):
                q_cursor = self._cursors["cross"]
            else:
                q_cursor = QCursor(square_pixmap(size))
        elif cursor == "circle":
            q_cursor = QCursor(circle_pixmap(size))
        elif cursor == "crosshair":
            q_cursor = QCursor(crosshair_pixmap())
        else:
            q_cursor = self._cursors[cursor]

        self.canvas.native.setCursor(q_cursor)

    def on_open_controls_dialog(self, event=None):
        """Open dialog responsible for layer settings."""
        raise NotImplementedError("Must implement method")

    def on_toggle_controls_dialog(self, _event=None):
        """Toggle between on/off state of the layer settings."""
        if self._disable_controls:
            return
        if self._layers_controls_dialog is None:
            self.on_open_controls_dialog()
        else:
            self._layers_controls_dialog.setVisible(not self._layers_controls_dialog.isVisible())

    @property
    def _canvas_corners_in_world(self):
        """Location of the corners of canvas in world coordinates.

        Returns
        -------
        corners : 2-tuple
            Coordinates of top left and bottom right canvas pixel in the world.
        """
        # Find corners of canvas in world coordinates
        top_left = self._map_canvas2world([0, 0])
        bottom_right = self._map_canvas2world(self.canvas.size)
        return np.array([top_left, bottom_right])

    def on_resize(self, event):
        """Called whenever canvas is resized.

        event : vispy.util.event.Event
            The vispy event that triggered this method.
        """
        self.viewer._canvas_size = tuple(self.canvas.size[::-1])

    def _process_mouse_event(self, mouse_callbacks, event):
        """Add properties to the mouse event before passing the event to the
        napari events system. Called whenever the mouse moves or is clicked.
        As such, care should be taken to reduce the overhead in this function.
        In future work, we should consider limiting the frequency at which
        it is called.

        This method adds following:
            position: the position of the click in world coordinates.
            view_direction: a unit vector giving the direction of the camera in
                world coordinates.
            dims_displayed: a list of the dimensions currently being displayed
                in the viewer. This comes from viewer.dims.displayed.
            dims_point: the indices for the data in view in world coordinates.
                This comes from viewer.dims.point

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
        try:
            event.view_direction = self.viewer.camera.calculate_nd_view_direction(
                self.viewer.dims.ndim, self.viewer.dims.displayed
            )
        except AttributeError:
            event.view_direction = None

        # Update the cursor position
        self.viewer.cursor._view_direction = event.view_direction
        self.viewer.cursor.position = self._map_canvas2world(list(event.pos))

        # Add the cursor position to the event
        event.position = self.viewer.cursor.position

        # Add the displayed dimensions to the event
        event.dims_displayed = list(self.viewer.dims.displayed)

        # Add the current dims indices
        event.dims_point = list(self.viewer.dims.point)

        # Put a read only wrapper on the event
        event = ReadOnlyWrapper(event)
        mouse_callbacks(self.viewer, event)

        layer = self.viewer.layers.selection.active
        if layer is not None:
            mouse_callbacks(layer, event)

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
        nd = self.viewer.dims.ndisplay
        transform = self.view.camera.transform.inverse
        mapped_position = transform.map(position)[:nd]
        position_world_slice = mapped_position[::-1]

        position_world = list(self.viewer.dims.point)
        for i, d in enumerate(self.viewer.dims.displayed):
            position_world[d] = position_world_slice[i]
        return tuple(position_world)

    def on_draw(self, _event):
        """Called whenever the canvas is drawn.

        This is triggered from vispy whenever new data is sent to the canvas or
        the camera is moved and is connected in the `QtViewer`.
        """
        for layer in self.viewer.layers:
            if layer.ndim <= self.viewer.dims.ndim:
                layer._update_draw(
                    scale_factor=1 / self.viewer.camera.zoom,
                    corner_pixels_displayed=self._canvas_corners_in_world[:, layer._displayed_axes],
                    shape_threshold=self.canvas.size,
                )

    def clipboard(self):
        """Take a screenshot of the currently displayed viewer and copy the image to the clipboard."""
        from qtextra.helpers import add_flash_animation

        img = self.canvas.native.grabFramebuffer()

        cb = QGuiApplication.clipboard()
        cb.setImage(img)
        add_flash_animation(self)

    def on_mouse_wheel(self, event):
        """Called whenever mouse wheel activated in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_wheel_callbacks, event)

    def on_mouse_press(self, event):
        """Called whenever mouse pressed in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_press_callbacks, event)

    def on_mouse_move(self, event):
        """Called whenever mouse moves over canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_move_callbacks, event)

    def on_mouse_release(self, event):
        """Called whenever mouse released in canvas.

        Parameters
        ----------
        event : vispy.event.Event
            The vispy event that triggered this method.
        """
        self._process_mouse_event(mouse_release_callbacks, event)

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.canvas._backend._keyEvent(self.canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.canvas._backend._keyEvent(self.canvas.events.key_release, event)
        event.accept()

    def closeEvent(self, event):
        """Cleanup and close.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        raise NotImplementedError("Must implement method")
