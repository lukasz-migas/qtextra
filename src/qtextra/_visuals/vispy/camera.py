"""Camera used by image/line plots."""

import numpy as np
from vispy.geometry import Rect
from vispy.scene import BaseCamera, Ellipse, PanZoomCamera, Polygon
from vispy.util import keys
from vispy.util.event import Event

from qtextra._visuals.interaction import ExtractEvent
from qtextra._visuals.interaction import Polygon as PolygonEvent


def to_rect(center, width, height):
    """Convert center."""
    left = center[0] - width / 2
    right = center[0] + width / 2
    bottom = center[1] - height / 2
    top = center[1] + height / 2
    return left, right, bottom, top


def round_to_half(*values):
    """Round values to nearest .5."""
    return np.round(np.asarray(values) * 2) / 2


class BoxZoomCamera(PanZoomCamera):
    """Custom zoom camera."""

    def __init__(self, parent, **kwargs):
        # round coordinates when dealing with 2d data
        self._round_coords = kwargs.pop("round_coords", False)
        # dictionary of callbacks to be used when user uses CTRL/SHIFT/ALT keys
        self._callbacks = kwargs.pop("callbacks", {})
        if self._callbacks is None:
            self._callbacks = {}
        # extents
        self._extents = None
        # flag to indicate that this is a 1d data
        self._is_1d: bool = kwargs.pop("is_1d", False)

        super().__init__(parent=parent, **kwargs)
        self.events.add(mouse_control=Event, zoom_box=Event, zoom_box_show=Event, zoom=Event)

        # keep track of keys
        self._key_control = False
        self._key_shift = False
        self._key_alt = False

        self.polygon = PolygonEvent()
        self.lock: bool = False
        self.allow_extraction: bool = True
        self.roi_shape: str = "rect"

    def reset_polygon(self):
        """Reset polygon."""
        self.polygon = PolygonEvent()
        self.roi_shape = "rect"
        self.lock = False

    def on_callback_poly(self):
        """Specialized callback function for polygon processing."""
        extract_evt = ExtractEvent(self.roi_shape, 0, 0, 0, 0, polygon=self.polygon)
        self._on_callback(extract_evt)
        self.polygon = PolygonEvent()

    def _on_callback(self, extract_evt: ExtractEvent):
        """Callbacks."""
        # process CTRL callbacks
        # if self._callbacks.get("CTRL", False) and isinstance(self._callbacks["CTRL"], list):
        #     for callback in self._callbacks["CTRL"]:
        #         pub.sendMessage(callback, event=extract_evt)
        # # process SHIFT callbacks
        # elif self._callbacks.get("SHIFT", False) and isinstance(self._callbacks["SHIFT"], list):
        #     for callback in self._callbacks["SHIFT"]:
        #         pub.sendMessage(callback, event=extract_evt)
        # # process ALT callbacks
        # elif self._callbacks.get("ALT", False) and isinstance(self._callbacks["ALT"], list):
        #     for callback in self._callbacks["ALT"]:
        #         pub.sendMessage(callback, event=extract_evt)

    def _on_callback_key(self, extract_evt: ExtractEvent, key: str):
        """Process callbacks."""
        # if self._callbacks.get(key, False) and isinstance(self._callbacks[key], list):
        #     for callback in self._callbacks[key]:
        #         pub.sendMessage(callback, event=extract_evt)

    def set_extents(self, xmin, xmax, ymin, ymax):
        """Set plot extents."""
        rect = Rect()
        rect.left = xmin
        rect.right = xmax
        rect.bottom = ymin
        rect.top = ymax
        self._extents = rect
        self._default_state["rect"] = rect

    def _check_zoom_limit(self, rect: Rect):
        """Check whether new range is outside of the allowed window."""
        if isinstance(rect, Rect) and self._extents is not None:
            limit_rect = self._extents
            if rect.left < limit_rect.left:
                rect.left = limit_rect.left
            if rect.right > limit_rect.right:
                rect.right = limit_rect.right
            if rect.bottom < limit_rect.bottom:
                rect.bottom = limit_rect.bottom
            if rect.top > limit_rect.top:
                rect.top = limit_rect.top
        return rect

    def _check_range(self, x0, x1, y0, y1):
        """Check whether values are correct."""
        if y1 < y0:
            y0, y1 = y1, y0
        if x1 < x0:
            x0, x1 = x1, x0
        if self._extents is not None:
            limit_rect = self._extents
            if x0 < limit_rect.left:
                x0 = limit_rect.left
            if x1 > limit_rect.right:
                x1 = limit_rect.right
            if y0 < limit_rect.bottom:
                y0 = limit_rect.bottom
            if y1 > limit_rect.top:
                y1 = limit_rect.top
        return x0, x1, y0, y1

    def _check_wheel(self, center) -> bool:
        """Check whether outside of range."""
        limit_rect = self._extents
        if not limit_rect:
            return True
        x, y, _, _ = center
        if x < limit_rect.left or x > limit_rect.right:
            return False
        if y < limit_rect.bottom or y > limit_rect.top:
            return False
        return True

    @property
    def extent(self):
        """X/Y-axes extent."""
        return self.rect.left, self.rect.right, self.rect.bottom, self.rect.top

    @property
    def x_extent(self):
        """X-axis extent."""
        return self.rect.left, self.rect.right

    @property
    def y_extent(self):
        """X-axis extent."""
        return self.rect.bottom, self.rect.top

    @property
    def rect(self):
        """Get rect."""
        return super().rect

    @rect.setter
    def rect(self, args):
        if isinstance(args, tuple):
            rect = Rect(*args)
        else:
            rect = Rect(args)

        # ensure user never goes outside of allowed limits
        rect = self._check_zoom_limit(rect)

        if self._rect != rect:
            self._rect = rect
            self.view_changed()

    def get_motion_msg(self, evt):
        """Parse motion message."""
        x1, y1, _, _ = self._transform.imap(np.asarray(evt.pos[:2]))
        if self._is_1d:
            return f"x={x1:.4f} y={y1:.4f}"
        else:
            if x1 < 0 or y1 < 1:
                return ""
            return f"x={int(x1)} y={int(y1)}"

    def viewbox_mouse_event(self, event):
        """
        The SubScene received a mouse event; update transform
        accordingly.

        Parameters
        ----------
        event : instance of Event
            The event.
        """

        def _zoom_callback():
            self._on_callback_key(
                ExtractEvent(self.roi_shape, self.rect.left, self.rect.right, self.rect.bottom, self.rect.top), "ZOOM"
            )

        def _event_callback(xy_values):
            self._on_callback(ExtractEvent(self.roi_shape, *xy_values))

        if event.handled or not self.interactive:  # or self._extents is None:
            return

        # Scrolling
        BaseCamera.viewbox_mouse_event(self, event)

        # mouse wheel zoom
        # pub.sendMessage("statusbar.update.coordinates", msg=self.get_motion_msg(event))

        if event.type == "mouse_wheel":
            center = self._scene_transform.imap(event.pos)
            if self._is_1d:
                center[1] = 0.0
            if self._check_wheel(center):
                self.zoom((1 + self.zoom_factor) ** (-event.delta[1] * 30), center)
                event.handled = True
                _zoom_callback()
                self.events.zoom(event=event)

        elif event.type == "mouse_move":
            if event.press_event is None:
                return

            # update keyboard modifiers
            modifiers = event.mouse_event.modifiers
            self._key_control = keys.CONTROL in modifiers
            self._key_shift = keys.SHIFT in modifiers
            self._key_alt = keys.ALT in modifiers

            # right-click -> panning
            if 2 in event.buttons and not modifiers:
                # Translate
                p1 = np.array(event.last_event.pos)[:2]
                p2 = np.array(event.pos)[:2]
                if self._is_1d:
                    p1[1], p2[1] = 0.0, 0.0
                p1s = self._transform.imap(p1)
                p2s = self._transform.imap(p2)
                self.pan(p1s - p2s)
                _zoom_callback()
                event.handled = True
            # left-click -> box-zoom
            else:
                if self.lock:
                    return

                # Zoom in/out
                x0, y0, _, _ = self._transform.imap(np.asarray(event.press_event.pos[:2]))
                x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
                x0, x1, y0, y1 = self._check_range(x0, x1, y0, y1)

                # if data is 1d, make sure to always show nice, full y-axis view
                if self._is_1d:
                    y0, _ = self.y_extent
                if self._round_coords:
                    x0, x1, y0, y1 = np.round([x0, x1, y0, y1]).astype(int)
                if self.roi_shape == "rect":
                    pos = np.asarray([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
                else:
                    w = x1 - x0
                    h = y1 - y0
                    c = (x0 + w / 3, y0 + h / 3)
                    pos = c, (w, h)
                # standard zoom
                if 1 in event.buttons and not modifiers:
                    self.events.zoom_box(event=event, pos=pos, color="white", roi_shape=self.roi_shape)
                # special types
                elif 1 in event.buttons and self._key_control:
                    self.events.zoom_box(event=event, pos=pos, color="red", roi_shape=self.roi_shape)
                elif 1 in event.buttons and self._key_shift:
                    self.events.zoom_box(event=event, pos=pos, color="blue", roi_shape=self.roi_shape)
                elif 1 in event.buttons and self._key_alt:
                    self.events.zoom_box(event=event, pos=pos, color="green", roi_shape=self.roi_shape)
                self.events.zoom_box_show(event=event, show=True, roi_shape=self.roi_shape)
                event.handled = True
        # left mouse press - start of drag and zoom event
        elif event.type == "mouse_press":
            # accept the event if it is button 1 or 2.
            # This is required in order to receive future events
            event.handled = event.button in [1, 2]
        # left mouse release - end of drag and zoom event
        elif event.type == "mouse_release":
            # add point to polygon but prevent the user from zooming-in
            if self.roi_shape == "poly" and self.lock:
                self.events.zoom_box_show(event=event, show=True, roi_shape=self.roi_shape)
                if event.press_event.button in [1]:
                    x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
                    self.polygon.add_point(*round_to_half(x1, y1))
                return
            self.events.zoom_box_show(event=event, show=False, roi_shape=self.roi_shape)  # changed
            if event.press_event.button not in [1]:
                return
            event.handled = event.button in [1, 2]

            # Zoom in/out
            x0, y0, _, _ = self._transform.imap(np.asarray(event.press_event.pos[:2]))
            x1, y1, _, _ = self._transform.imap(np.asarray(event.pos[:2]))
            x0, x1, y0, y1 = self._check_range(x0, x1, y0, y1)
            # if data is 1d, make sure to always show nice, full y-axis view
            if self._is_1d:
                y0, _ = self.y_extent

            if self._key_control and self.allow_extraction:
                _event_callback((x0, x1, y0, y1))
            elif self._key_shift and self.allow_extraction:
                _event_callback((x0, x1, y0, y1))
            elif self._key_alt and self.allow_extraction:
                _event_callback((x0, x1, y0, y1))
            else:
                if x1 - x0 <= 0.00001 or y1 - y0 <= 0.00001:
                    return
                self.simple_zoom(x0, x1, y0, y1)
                _zoom_callback()
        else:
            event.handled = False

    def draw_polygon(self, force: bool = False):
        """Draw polygon."""
        pos = self.polygon.get_polygon_vispy()
        event = Event("polygon")
        if len(pos) < 2:
            self.events.zoom_box_show(event=event, show=False, roi_shape=self.roi_shape)
        if force:
            self.events.zoom_box_show(event=event, show=True, roi_shape=self.roi_shape)
        self.events.zoom_box(event=event, pos=pos, color="#FFFFFF", roi_shape=self.roi_shape)

    def reset(self):
        """Reset axes."""
        event = Event("reset_event")
        self.events.zoom_box_show(event=event, show=False, roi_shape=self.roi_shape)
        super().reset()
        self._on_callback_key(
            ExtractEvent("rect", self.rect.left, self.rect.right, self.rect.bottom, self.rect.top), "ZOOM"
        )
        self.events.zoom(event=event)

    def simple_zoom(self, x0, x1, y0, y1):
        """Zoom-in on specified x/y-axis limits."""
        rect = Rect(self.rect)
        rect.left = x0
        rect.right = x1
        rect.bottom = y0
        rect.top = y1
        self.rect = rect
        self.events.zoom(event=Event("event"))

    @property
    def callbacks(self):
        """PubSub callbacks."""
        return self._callbacks

    @callbacks.setter
    def callbacks(self, callbacks):
        if callbacks is None:
            callbacks = {}
        for key in callbacks:
            if not isinstance(callbacks[key], (list, tuple)):
                callbacks[key] = [callbacks[key]]
        self._callbacks = callbacks

    @property
    def zoom_value(self):
        """float: Scale from canvas pixels to world pixels."""
        canvas_size = np.min(self.canvas.size)
        scale = np.min([self.rect.width, self.rect.height])
        zoom = canvas_size / scale
        return zoom

    @zoom_value.setter
    def zoom_value(self, zoom):
        if self.zoom_value == zoom:
            return
        scale = np.min(self.canvas.size) / zoom
        # Set view rectangle, as left, right, width, height
        corner = np.subtract(self.center[:2], scale / 2)
        self.rect = (*tuple(corner), scale, scale)

    @property
    def x_range(self):
        """Return x-axis range."""
        return self.rect.width


class BoxZoomCameraMixin:
    """Mixin class to nicely setup box-zoom camera."""

    view = None

    def __init__(self, **kwargs):
        color = kwargs.pop("color", (1.0, 0.0, 1.0, 0.5))
        border_color = kwargs.pop("border_color", "white")
        # set camera
        self.view.camera = BoxZoomCamera(parent=self.view.scene, **kwargs)
        self.view.camera.events.mouse_control.connect(self._on_mouse_control)
        self.view.camera.events.zoom_box.connect(self._on_zoom_box)
        self.view.camera.events.zoom_box_show.connect(self._on_zoom_box_visible)

        # main polygon
        self._zoom_roi = Polygon(parent=self.view.scene, color=color, border_color=border_color, border_width=4)
        self._zoom_roi.visible = False
        # main ellipse
        self._zoom_ellipse = Ellipse(
            (0, 0), parent=self.view.scene, color=color, border_color=border_color, border_width=4
        )
        self._zoom_ellipse.visible = False

    def _on_mouse_control(self, event):
        """Process mouse double click event."""

    def _on_mouse_double_click(self, event):
        """Process mouse double click event."""
        if 1 == event.button:
            self.view.camera.reset()

    def _on_zoom_box(self, event):
        """Handle zoom."""
        try:
            if event.roi_shape == "circle":
                self._zoom_ellipse.center = event.pos[0]
                self._zoom_ellipse.radius = event.pos[1]
                self._zoom_ellipse.border_color = event.color
            else:
                self._zoom_roi.pos = event.pos
                self._zoom_roi.border_color = event.color
        except ValueError:
            pass

    def _on_zoom_box_visible(self, event):
        """Handle zoom."""
        if event.roi_shape == "rect":
            self._zoom_roi.visible = True if event.show else False
            if not event.show:
                self._zoom_roi.pos = [[0, 0], [1, 1]]
        elif event.roi_shape == "circle":
            self._zoom_ellipse.visible = True if event.show else False
            if not event.show:
                self._zoom_roi.pos = [[0, 0], [1, 1]]
