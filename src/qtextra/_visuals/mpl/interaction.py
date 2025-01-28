"""Interaction."""

import typing as ty

import numpy as np
from koyo.system import IS_MAC
from loguru import logger
from matplotlib.backend_bases import MouseButton
from matplotlib.legend import Legend
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QCursor, QGuiApplication, QPen
from qtpy.QtWidgets import QWidget

from qtextra._visuals.interaction import ExtractEvent, Polygon, get_center
from qtextra._visuals.mpl.gids import PlotIds

# TODO: add new class to handle return of extraction windows to enable better handling of different rois


def reset_visible(axes):
    """Reset visible axes."""
    for line in axes.lines:
        line.set_clip_on(True)
    for t in axes.texts:
        t.set_visible(True)


class MPLInteraction(QWidget):
    """Improved matplotlib interaction."""

    # signals
    evt_key = Signal(str)

    evt_ctrl = Signal(list, list, list)
    evt_shift = Signal(list, list, list)
    evt_alt = Signal(list, list, list)
    evt_view_activate = Signal(str)

    evt_move = Signal(tuple)
    evt_pick = Signal(object)
    evt_wheel = Signal()
    evt_pressed = Signal()
    evt_double_click = Signal()
    evt_released = Signal()
    evt_ctrl_changed = Signal(bool)
    evt_ctrl_released = Signal(tuple)
    evt_ctrl_double_click = Signal(tuple)

    def __init__(
        self,
        axes,
        data_limits=None,
        plot_id: ty.Optional[str] = None,
        allow_extraction: bool = True,
        allow_drag: bool = False,
        callbacks: ty.Optional[dict] = None,
        parent: QWidget = None,
        is_joint: bool = False,
        is_heatmap: bool = False,
        obj=None,
        zoom_color=Qt.black,
        roi_shape: str = "rect",
    ):
        QWidget.__init__(self)
        self.parent = parent
        self.axes = None
        self.canvas = None
        self.mpl_events = []
        self.plot_id = plot_id
        self.allow_extraction = allow_extraction
        self.allow_drag = allow_drag
        self.is_joint = is_joint
        self.is_heatmap = is_heatmap
        self.data_object = obj
        self.roi_shape = roi_shape
        self.lock = False
        self.poly_dialog = None

        self.axes, self._callbacks, data_limits = self.validate_input(axes, callbacks, data_limits)

        self.active = True  # for activation / deactivation
        self.background = None
        self.dragged = None
        self._is_inside_axes = True
        self.prevent_sync_zoom = False

        self.useblit = True
        self.valid_buttons = [MouseButton.LEFT]

        # flags
        self._trigger_extraction = False
        self._is_label = False
        self._is_legend = False
        self._is_patch = False
        self._is_1d = True

        # events
        self.polygon = Polygon()
        self._xy_press = []
        self.evt_press = None
        self.evt_release = None
        self.pick_pos = None
        self._ctrl_key = False
        self._alt_key = False
        self._shift_key = False
        self._space_key = False
        self._button_down = False
        self._key_press = False

        self._color_normal = zoom_color  # Qt.black
        self._color_ctrl = Qt.red

        self.bind_plot_events(axes)
        self.set_data_limits(data_limits)

    @staticmethod
    def validate_input(axes, callbacks, data_limits):
        """Validate input to ensure correct parameters are being used."""
        if not isinstance(axes, list):
            axes = list(axes)

        if callbacks is None:
            callbacks = {}
        for key in callbacks:
            if not isinstance(callbacks[key], (list, tuple)):
                callbacks[key] = [callbacks[key]]

        if not all(isinstance(elem, (list, tuple)) for elem in data_limits):
            data_limits = [data_limits]

        return axes, callbacks, data_limits

    def reset_polygon(self):
        """Reset polygon."""
        self.polygon = Polygon()
        self.roi_shape = "rect"
        self.lock = False

    def set_data_limits(self, data_limits):
        """Set data limits on the axes object."""
        if len(data_limits) != len(self.axes):
            raise ValueError("Incorrect `data_limits` input")

        for i, _ in enumerate(self.axes):
            self.axes[i].data_limits = data_limits[i]

    def update_handler(self, data_limits=None, obj=None, **kwargs):
        """Update zoom parameters."""
        self.set_data_limits(data_limits)
        self.data_object = obj

    def update_extents(self, data_limits=None):
        """Update plot extents."""
        if data_limits is not None:
            self.set_data_limits(data_limits)

    def on_pick(self, event):
        """Store which text object was picked and were the pick event occurs."""
        self._is_label = False
        self._is_legend = False
        self._is_patch = False

        if isinstance(event.artist, Text):
            self.dragged = event.artist
            self.pick_pos = (event.mouseevent.xdata, event.mouseevent.ydata)
            self._is_label = True
        elif isinstance(event.artist, Legend):
            self.dragged = event.artist
            self._is_legend = True
        elif isinstance(event.artist, Rectangle):
            if event.artist.get_picker():
                self.dragged = event.artist
                self.pick_pos = (self.dragged.get_width() / 2, self.dragged.get_height() / 2)
                self._is_patch = True
        self.evt_pick.emit(self.pick_pos)
        return True

    def bind_plot_events(self, axes):
        """Bind events."""
        # remove any previous events connected to the canvas
        if self.canvas is not axes[0].figure.canvas:
            for event in self.mpl_events:
                self.canvas.mpl_disconnect(event)

        for ax in axes:
            self.canvas = ax.figure.canvas
            # pick events
            self.mpl_events.append(self.canvas.mpl_connect("pick_event", self.on_pick))

            # button events
            self.mpl_events.append(self.canvas.mpl_connect("scroll_event", self.on_wheel))
            self.mpl_events.append(self.canvas.mpl_connect("button_press_event", self.on_press))
            self.mpl_events.append(self.canvas.mpl_connect("button_release_event", self.on_release))

            # keyboard events
            self.mpl_events.append(self.canvas.mpl_connect("key_press_event", self.on_key_state))
            self.mpl_events.append(self.canvas.mpl_connect("key_release_event", self.on_key_state))

            # enter events
            self.mpl_events.append(self.canvas.mpl_connect("axes_enter_event", self.on_enter_axes))
            self.mpl_events.append(self.canvas.mpl_connect("axes_leave_event", self.on_leave_axes))

            # motion events
            self.mpl_events.append(self.canvas.mpl_connect("motion_notify_event", self.on_key_state))
            self.mpl_events.append(self.canvas.mpl_connect("motion_notify_event", self.on_motion))

            # draw events
            self.mpl_events.append(self.canvas.mpl_connect("draw_event", self.update_background))

        # Pre-set keys
        self._shift_key = False
        self._ctrl_key = False
        self._alt_key = False
        self._key_press = False
        self._trigger_extraction = False
        self._button_down = False

    @property
    def color(self) -> QColor:
        """Return color based on whether the ctrl key is pressed."""
        if self._ctrl_key and self.allow_extraction:
            return self._color_ctrl
        return self._color_normal

    @property
    def dpi_ratio(self) -> float:
        """Return DPI ratio."""
        from qtextra.event_loop import _app_ref

        app = _app_ref
        dpi = float(app.screens()[0].physicalDotsPerInch())
        return dpi

    @property
    def is_extracting(self) -> bool:
        """Returns if user is extracting data."""
        return self._trigger_extraction and self.allow_extraction

    def on_enter_axes(self, evt):
        """Flag that mouse has entered the axes."""
        self._reset_keys()

    def on_leave_axes(self, evt):
        """Flag that mouse has left the axes."""
        self._reset_keys()

    def on_key_state(self, evt):
        """Update state of the key."""
        _modifiers = QGuiApplication.keyboardModifiers()

        self._key_press = evt.key is not None
        key = "" if evt.key is None else evt.key
        ctrl_before = self._ctrl_key
        self._ctrl_key = "control" in key if not IS_MAC else "cmd" in key  # use command key on mac
        self._shift_key = "shift" in key
        self._alt_key = "alt" in key
        self._trigger_extraction = False
        self.evt_key.emit(key)
        if ctrl_before != self._ctrl_key:
            self.evt_ctrl_changed.emit(self._ctrl_key)

    def _reset_keys(self):
        """Utility function to reset keys whenever user enters/leaves the axes."""
        self._shift_key = False
        self._ctrl_key = False
        self._alt_key = False
        self._key_press = False
        self._trigger_extraction = False

    def update_background(self, _evt):
        """Force an update of the background."""
        if self.useblit:
            self.background = self.canvas.copy_from_bbox(self.canvas.figure.bbox)

    def ignore(self, evt):
        """Check whether an event should be ignored."""
        # If zoom-box is not active :
        if not self.active:
            return True

        # If canvas was locked
        if not self.canvas.widgetlock.available(self):
            return True

        if self.valid_buttons is not None:
            if evt.button in self.valid_buttons and not self._key_press:
                pass
            elif evt.button in self.valid_buttons and self._ctrl_key:
                self._trigger_extraction = True
            else:
                if evt.button == MouseButton.MIDDLE:
                    return True
                elif evt.button == MouseButton.RIGHT and self.evt_release is None:
                    return True
                else:
                    return False

        # If no button pressed yet or if it was out of the axes, ignore
        if self.evt_press is None:
            return evt.inaxes not in self.axes

        # If a button pressed, check if the on_release-button is the same
        return evt.inaxes not in self.axes or evt.button != self.evt_press.button

    def on_wheel(self, evt, base_scale: float = 1.25):
        """Wheel event."""
        self.evt_view_activate.emit(self.plot_id)

        xdata = evt.xdata  # get event x location
        direction = evt.button

        if direction == "up":
            scale_factor = 1 / base_scale
        elif direction == "down":
            scale_factor = base_scale
        else:
            scale_factor = 1

        try:
            for ax in self.canvas.figure.get_axes():
                cur_xlim = ax.get_xlim()
                # cur_ylim = ax.get_ylim()
                new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
                # new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

                relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
                # rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
                new_xlim = [xdata - new_width * (1 - relx), xdata + new_width * relx]
                if hasattr(ax, "plot_limits"):
                    xmin, xmax, ymin, ymax = ax.plot_limits
                    new_xlim = [max(xmin, new_xlim[0]), min(xmax, new_xlim[1])]

                ax.set_xlim(new_xlim)
            # ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])

            # new_xlim = [x - (x - cur_xlim[0]) * scale_factor, x + (cur_xlim[1] - x) * scale_factor]
            # new_ylim = [y - (y - cur_ylim[0]) * scale_factor, y + (cur_ylim[1] - y) * scale_factor]
            # ax.set_xlim(new_xlim)
            # ax.set_ylim(new_ylim)
        except TypeError:
            pass
        self.canvas.draw()
        if scale_factor != 1:
            self.evt_wheel.emit()

    def on_press(self, evt):
        """Event on button press."""
        self.evt_view_activate.emit(self.plot_id)

        self.evt_press = evt
        # Is the correct button pressed within the correct axes?
        if self.ignore(evt):
            return

        self.evt_pressed.emit()

        x, y = evt.x, evt.y

        # keep track of where the user clicked first
        self._xy_press = []
        for a in self.canvas.figure.get_axes():
            if x is not None and y is not None and a.in_axes(evt) and a.get_navigate() and a.can_zoom():
                self._xy_press.append((x, y, a))

        # dragging annotation
        if self.dragged is not None and not evt.dblclick:
            if self._is_legend or self._is_label:
                return
        self._button_down = True

        if self.evt_press.dblclick and self.is_extracting:
            x, y = evt.xdata, evt.ydata
            self.evt_ctrl_double_click.emit((x, y))
            return

        # started panning
        if evt.button == MouseButton.RIGHT:
            self.canvas.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
            for x, y, a in self._xy_press:
                a.start_pan(x, y, MouseButton.LEFT)
        return False

    def on_motion(self, evt):
        """Event on motion."""
        # send event
        if evt.xdata is not None and evt.ydata is not None:
            self.evt_move.emit((evt.xdata, evt.ydata))
        #     pub.sendMessage("statusbar.update.coordinates", msg=self.get_motion_msg(evt))

        # drag label
        if self.dragged is not None:
            if self._is_label:
                self._drag_label(evt, False)
            elif self._is_patch:
                self._drag_patch(evt, False)
            return

        self._trigger_extraction = self._ctrl_key

        # show rubberband
        if evt.button == MouseButton.LEFT and self._xy_press:
            last_x, last_y, a, x, y = self.parse_motion_evt(evt)
            (x1, y1), (x2, y2) = np.clip([[last_x, last_y], [x, y]], a.bbox.min, a.bbox.max)
            if evt.key is not None:
                if "x" in evt.key or (self.is_extracting and self._is_1d):
                    y1, y2 = a.bbox.intervaly
                elif "y" in evt.key:
                    x1, x2 = a.bbox.intervalx
            self.draw_rubberband(evt, x1, y1, x2, y2)
        # draw polygon
        elif self.roi_shape == "poly" and self.lock:
            self.drawRectangle("poly")
        # pan
        elif evt.button == MouseButton.RIGHT and self._xy_press:
            evt_x, evt_y = evt.x, evt.y
            if self._is_1d:
                _, evt_y, a, evt_x, _ = self.parse_motion_evt(evt)
            for _, _, a in self._xy_press:
                # safer to use the recorded button at the press than current button:
                # multiple button can get pressed during motion...
                a.drag_pan(MouseButton.LEFT, evt.key, evt_x, evt_y)
            self.canvas.draw()

    def on_release(self, evt):
        """Event on button release."""
        if self.evt_press is None or (self.ignore(evt) and not self._button_down):
            return
        self.drawRectangle(None)
        self._button_down = False
        self.canvas.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        # drag label
        if self.dragged is not None:
            if self._is_label:
                self._drag_label(evt)
            elif self._is_legend:
                self._drag_legend(evt)
            elif self._is_patch:
                self._drag_patch(evt)
            return

        # on_release coordinates, button, ...
        self.evt_release = evt

        try:
            xmin, xmax, ymin, ymax, evt = self.calculate_new_limits(evt)
        except IndexError:
            self.evt_released.emit()
            return

        # adding point to polygon
        if self.roi_shape == "poly" and self.lock:
            # add polygon point that is nearest to the half
            self.polygon.add_point(*round_to_half(self.evt_press.xdata, self.evt_press.ydata))
            self.evt_released.emit()
            return

        if self.is_extracting:
            self.on_callback(xmin, xmax, ymin, ymax, evt)
            self.canvas.draw()
            self.evt_released.emit()
            self.evt_ctrl_released.emit((xmin, xmax, ymin, ymax))
            return
        elif self._trigger_extraction and not self.allow_extraction:
            logger.warning("Cannot extract data at this moment...")
            self.canvas.draw()
            self.evt_released.emit()
            return

        if self.lock:
            logger.debug("Drag zoom is disabled - you must unlock it first or replot.")
            self.evt_released.emit()
            return

        # left-click + ctrl OR double left click reset axes
        if self.evt_press.dblclick:
            if self.is_extracting:
                x, y = evt.x, evt.y
                self.evt_ctrl_double_click.emit((x, y))
                logger.debug("Cannot double-click zoom-out while holding CTRL")
                return
            self._zoom_out(evt)
            self.evt_double_click.emit()
            self.evt_released.emit()
            return

        # zoom in the plot area
        if evt.button == MouseButton.LEFT:
            x, y = evt.x, evt.y
            for last_x, last_y, a in self._xy_press:
                # allow cancellation of the zoom-in if the spatial distance is too small (5 pixels)
                if (abs(x - last_x) < 3 and evt.key != "y") or (abs(y - last_y) < 3 and evt.key != "x"):
                    self._xy_press = None
                    self.canvas.draw()
                    return
                twin_x, twin_y = False, False
                a._set_view_from_bbox((last_x, last_y, x, y), "in", evt.key, twin_x, twin_y)
                self._on_callback_key(ExtractEvent(self.roi_shape, xmin, xmax, ymin, ymax), "ZOOM")
                if self.is_joint:
                    self._handle_joint(False)
            self.canvas.draw()
        elif self.allow_drag and evt.button == MouseButton.RIGHT:
            for _, _, a in self._xy_press:
                a.end_pan()
                self._on_callback_key(ExtractEvent(self.roi_shape, *a.get_xlim(), *a.get_ylim()), "ZOOM")

        # reset triggers
        if self._trigger_extraction:
            self._trigger_extraction = False
        self.evt_released.emit()

    def get_motion_msg(self, evt) -> str:
        """Parse motion event."""
        msg = f"x={evt.xdata:.4f} y={evt.ydata:.4f}"
        return msg if not self._ctrl_key else f"[EXTRACT] {msg}"

    def parse_motion_evt(self, evt):
        """Get motion evt."""
        x, y = evt.x, evt.y
        last_x, last_y, a = self._xy_press[0]
        return last_x, last_y, a, x, y

    def on_callback(self, xmin, xmax, ymin, ymax, evt):
        """Process callback."""
        # parse extraction limits through cleanup
        xmin, xmax, ymin, ymax = self._parse_extraction_limits(xmin, xmax, ymin, ymax, evt)
        x_labels, y_labels = self.get_labels()

        extract_evt = ExtractEvent(self.roi_shape, xmin, xmax, ymin, ymax, x_labels=x_labels, y_labels=y_labels)

        self._on_callback(extract_evt)
        self.polygon = Polygon()

    def on_callback_poly(self):
        """Specialized callback function for polygon processing."""
        x_labels, y_labels = self.get_labels()
        extract_evt = ExtractEvent(
            self.roi_shape, 0, 0, 0, 0, x_labels=x_labels, y_labels=y_labels, polygon=self.polygon
        )
        self._on_callback(extract_evt)
        self.polygon = Polygon()

    def _on_callback(self, extract_evt):
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

    def _parse_extraction_limits(self, xmin, xmax, ymin, ymax, _evt):
        """Special parsing of x/y-limits for data extraction that supports multi-plot behaviour."""
        # special behaviour for joint plots
        plot_gid = self.evt_press.inaxes.get_gid()

        # check whether its a joint plot
        if self.is_joint:
            # top plot - need to update y-axis
            if plot_gid == PlotIds.PLOT_JOINT_X:
                _, _, ymin, ymax = self.axes[0].plot_limits
            elif plot_gid == PlotIds.PLOT_JOINT_Y:
                xmin, xmax, _, _ = self.axes[0].plot_limits
        return xmin, xmax, ymin, ymax

    def draw_rubberband(self, evt, x0, y0, x1, y1):
        """Draw box to highlight the currently selected region."""
        height = self.canvas.figure.bbox.height
        y1 = height - y1
        y0 = height - y0
        rect = [int(val) for val in (x0, y0, x1 - x0, y1 - y0)]
        self.drawRectangle(rect)

    def drawRectangle(self, rect):
        """Draw rectangle."""
        # Draw the zoom rectangle to the QPainter.  _draw_rect_callback needs
        # to be called at the end of paintEvent.

        dpi = self.devicePixelRatioF()
        if rect == "poly" and self._xy_press:

            def _draw_rect_callback(painter):
                pen = QPen(self.color, 2 / dpi, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawPolygon(
                    self.polygon.get_polygon(self.canvas.figure.get_axes()[0], dpi, self.canvas.figure.bbox.height)
                )

        elif rect not in [None, "poly"]:

            def _draw_rect_callback(painter):
                pen = QPen(self.color, 2 / dpi, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                # whenever zooming, always draw rectangle
                if not self.is_extracting:
                    painter.drawRect(*(pt / dpi for pt in rect))
                # when extracting, we can draw rectangle, circle or polygon (not yet)
                else:
                    if self.roi_shape == "rect":
                        painter.drawRect(*(pt / dpi for pt in rect))
                    elif self.roi_shape == "circle":
                        painter.drawEllipse(*(pt / dpi for pt in rect))
                    else:
                        painter.drawRect(*(pt / dpi for pt in rect))

        else:

            def _draw_rect_callback(painter):
                return

        self.canvas._draw_rect_callback = _draw_rect_callback
        self.update()

    def _handle_joint(self, zoom_out: bool):
        """Handle joint plot.

        This function will automatically update joint plots (x, y) with new data whenever user zooms-in or zooms-out
        """
        if self.data_object is None or (len(self.axes) == 3 and self.is_joint):
            return

        # get current limits
        if not zoom_out:
            xmin, xmax = self.axes[0].get_xlim()
            ymin, ymax = self.axes[0].get_ylim()
            ax_x_y = self.data_object.get_x_for_roi(xmin, xmax, ymin, ymax)
            ax_y_y = self.data_object.get_y_for_roi(xmin, xmax, ymin, ymax)
        else:
            ax_x_y = self.data_object.xy
            ax_y_y = self.data_object.yy

        for line in self.axes[1].get_lines():
            gid = line.get_gid()
            if gid == PlotIds.PLOT_JOINT_X:
                _y = ax_x_y if line.get_xdata().shape == ax_x_y.shape else ax_y_y
                line.set_ydata(_y)
                self.axes[1].set_ylim(0, _y.max())
                break

        for line in self.axes[2].get_lines():
            gid = line.get_gid()
            if gid == PlotIds.PLOT_JOINT_Y:
                _x = ax_y_y if line.get_xdata().shape == ax_y_y.shape else ax_x_y
                line.set_xdata(_x)
                self.axes[2].set_xlim(_x.min(), _x.max())
                break

    def _zoom_out(self, evt):
        # Check if a zoom out is necessary
        # zoom_out = False
        # for axes in self.axes:
        #     xmin, ymin, xmax, ymax = self._check_xy_values(*axes.data_limits)
        # if axes.get_xlim() != (xmin, xmax) and axes.get_ylim() != (ymin, ymax):
        #     zoom_out = True

        # Register a click if zoom out was not necessary
        # if not zoom_out:
        #     if evt.button == MouseButton.LEFT:
        #         pub.sendMessage("left_click", xpos=evt.xdata, ypos=evt.ydata)

        for axes in self.axes:
            xmin, ymin, xmax, ymax = self._check_xy_values(*axes.data_limits)

            # reset y-axis
            if self._shift_key or evt.key == "y":
                axes.set_ylim(ymin, ymax)
            # reset x-axis
            elif self._alt_key or evt.key == "x":
                axes.set_xlim(xmin, xmax)
            # reset both axes
            else:
                axes.set_xlim(xmin, xmax)
                axes.set_ylim(ymin, ymax)
                reset_visible(axes)
            self._on_callback_key(ExtractEvent(self.roi_shape, xmin, xmax, ymin, ymax), "ZOOM")

        # update axes
        if self.is_joint:
            self._handle_joint(True)

        self.canvas.draw()

    def _drag_label(self, evt, reset=True):
        """Move label, update its position and reset dragged object."""
        x, y = evt.xdata, evt.ydata

        if evt.key == "x":
            _, y = self.dragged.get_position()
        elif evt.key == "y":
            x, _ = self.dragged.get_position()

        new_pos = (x, y)
        if None not in new_pos:
            self.dragged.set_position(new_pos)
        self.canvas.draw()  # redraw image

        if reset:
            # if self.dragged.obj_name is not None:
            #     if self._callbacks.get("MOVE_LABEL", None):
            #         pub.sendMessage(self._callbacks["MOVE_LABEL"], label_obj=self.dragged)
            self._is_label = False
            self.dragged = None

    def _drag_legend(self, _evt):
        """Drag legend post-event."""
        self._is_legend = False
        self.dragged = None

    def _drag_patch(self, evt, reset=True):
        """Drag patch, update its position and reset dragged object."""
        width, height = self.pick_pos
        x = evt.xdata - width
        y = evt.ydata - height
        if evt.key == "x":
            _, y = self.dragged.get_xy()
        elif evt.key == "y":
            x, _ = self.dragged.get_xy()

        self.dragged.set_xy((x, y))
        self.canvas.draw()  # redraw image

        if reset:
            # if self.dragged.obj_name is not None:
            #     if self._callbacks["MOVE_PATCH"]:
            #         pub.sendMessage(self._callbacks["MOVE_PATCH"], patch_obj=self.dragged)
            self._is_patch = False
            self.dragged = None

    def get_labels(self):
        """Collects labels."""
        x_labels, y_labels = [], []
        for axes in self.axes:
            x_label = axes.get_xlabel()
            if x_label:
                x_labels.append(x_label)
            y_label = axes.get_ylabel()
            if y_label:
                y_labels.append(y_label)

        return list(set(x_labels)), list(set(y_labels))

    def calculate_new_limits(self, evt):
        """Calculate new plot limits."""
        # Just grab bounding box
        last_x, last_y, ax = self._xy_press[0]
        x, y = evt.x, evt.y
        twin_x, twin_y = False, False

        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()

        # zoom to rect
        inverse = ax.transData.inverted()
        (last_x, last_y), (x, y) = inverse.transform([(last_x, last_y), (x, y)])

        if twin_x:
            x0, x1 = x_min, x_max
        else:
            if x_min < x_max:
                if x < last_x:
                    x0, x1 = x, last_x
                else:
                    x0, x1 = last_x, x
                if x0 < x_min:
                    x0 = x_min
                if x1 > x_max:
                    x1 = x_max
            else:
                if x > last_x:
                    x0, x1 = x, last_x
                else:
                    x0, x1 = last_x, x
                if x0 > x_min:
                    x0 = x_min
                if x1 < x_max:
                    x1 = x_max

        if twin_y:
            y0, y1 = y_min, y_max
        else:
            if y_min < y_max:
                if y < last_y:
                    y0, y1 = y, last_y
                else:
                    y0, y1 = last_y, y
                if y0 < y_min:
                    y0 = y_min
                if y1 > y_max:
                    y1 = y_max
            else:
                if y > last_y:
                    y0, y1 = y, last_y
                else:
                    y0, y1 = last_y, y
                if y0 > y_min:
                    y0 = y_min
                if y1 < y_max:
                    y1 = y_max

        return x0, x1, y0, y1, evt

    def update(self):
        """Draw using newfangled blit draw depending on useblit."""
        if self.useblit:
            if self.background is not None:
                self.canvas.restore_region(self.background)
            self.canvas.blit(self.canvas.figure.bbox)
        else:
            self.canvas.draw_idle()

    def reset_axes(self, axis_pos):
        """Reset plot limits."""
        # Register a click if zoom-out was not necessary
        for axes in self.axes:
            xmin, ymin, xmax, ymax = self._check_xy_values(*axes.data_limits)

            if axis_pos in ["left", "right"]:
                axes.set_ylim(ymin, ymax)
            elif axis_pos in ["top", "bottom"]:
                axes.set_xlim(xmin, xmax)
            reset_visible(axes)
            self.canvas.draw()

    @staticmethod
    def _check_xy_values(xmin, ymin, xmax, ymax):
        if xmin > xmax:
            xmin, xmax = xmax, xmin
        if ymin > ymax:
            ymin, ymax = ymax, ymin
        # assure that x and y values are not equal
        if xmin == xmax:
            xmax = xmin * 1.0001
        if ymin == ymax:
            ymax = ymin * 1.0001
        return xmin, ymin, xmax, ymax


class ImageMPLInteraction(MPLInteraction):
    """Slightly altered interaction."""

    def __init__(
        self,
        axes,
        arrays,
        data_limits=None,
        plot_id: ty.Optional[str] = None,
        allow_extraction: bool = True,
        allow_drag: bool = True,
        callbacks: ty.Optional[dict] = None,
        parent: QWidget = None,
        is_joint: bool = False,
        is_heatmap: bool = False,
        obj=None,
        zoom_color=Qt.black,
    ):
        MPLInteraction.__init__(
            self,
            axes,
            data_limits=data_limits,
            plot_id=plot_id,
            allow_extraction=allow_extraction,
            allow_drag=allow_drag,
            callbacks=callbacks,
            parent=parent,
            is_joint=is_joint,
            is_heatmap=is_heatmap,
            obj=obj,
            zoom_color=zoom_color,
        )
        self.arrays = arrays
        self._is_1d = False
        shape = arrays[0].shape
        self._aspect_ratio = shape[0] / shape[1]

    def get_motion_msg(self, evt) -> str:
        """Parse motion event."""
        x, y = int(evt.xdata), int(evt.ydata)
        try:
            z = self.arrays[0][y, x]
        except IndexError:
            z = np.nan
        if not isinstance(z, np.ndarray):
            z = "" if np.isnan(z) else z
        msg = f"x={x} y={y} {z}"
        return msg if not self._ctrl_key else f"[EXTRACT] {msg}"

    def parse_motion_evt(self, evt):
        """Get motion evt."""
        x, y = evt.x, evt.y
        last_x, last_y, ax = self._xy_press[0]
        # convert to data dimension
        inverse = ax.transData.inverted()
        (last_x, last_y), (x, y) = inverse.transform([(last_x, last_y), (x, y)])
        last_x, last_y, x, y = np.round([last_x, last_y, x, y]).astype(int)
        # convert to bbox dimension
        (last_x, last_y), (x, y) = ax.transData.transform([(last_x, last_y), (x, y)])
        return last_x, last_y, ax, x, y

    def update_handler(self, data_limits=None, obj=None, arrays=None, **kwargs):
        """Update zoom parameters."""
        self.set_data_limits(data_limits)
        self.data_object = obj
        self.arrays = arrays

    def calculate_new_limits(self, evt):
        """Calculate new limits."""
        # first we need to calculate the extraction windows which might differ from zoom window
        _xmin, _xmax, _ymin, _ymax, evt = super().calculate_new_limits(evt)
        _xmin, _xmax, _ymin, _ymax = np.round([_xmin, _xmax, _ymin, _ymax]).astype(int)

        # preset the min/max values
        xmin, xmax, ymin, ymax = _xmin, _xmax, _ymin, _ymax

        # adjust the size to ensure proper image shape
        _shape = [_ymax - _ymin, _xmax - _xmin]
        _aspect_ratio = get_aspect_ratio(_shape)

        # adjust the width of the plot if the the aspect ratio is too high
        if _aspect_ratio > self._aspect_ratio:
            x_center = get_center(_xmin, _xmax)
            width = _shape[1]
            while get_aspect_ratio([_shape[0], width]) > self._aspect_ratio:
                width += 1
            width /= 2
            xmin, xmax = x_center - width, x_center + width
        # adjust the height of the plot if the aspect ratio is too small
        elif _aspect_ratio < self._aspect_ratio:
            y_center = get_center(_ymin, _ymax)
            height = _shape[0]
            while get_aspect_ratio([height, _shape[1]]) < self._aspect_ratio:
                height += 1
            height /= 2
            ymin, ymax = y_center - height, y_center + height
        # ensures that we have square, rounded edges
        xmin, xmax, ymin, ymax = np.round([xmin, xmax, ymin, ymax]).astype(int)

        # transform from data domain to pixel domain
        _, _, ax = self._xy_press[0]
        (last_x, last_y), (x, y) = ax.transData.transform([(xmin, ymin), (xmax, ymax)])
        self._xy_press[0] = (last_x, last_y, ax)
        evt.x, evt.y = x, y
        return _xmin, _xmax, _ymin, _ymax, evt


def get_aspect_ratio(shape) -> float:
    """Calculate aspect ratio."""
    return shape[0] / shape[1]


def round_values(*vals):
    """Round values to integers."""
    return np.round(vals).astype(np.int32)


def round_to_half(*vals):
    """Round values to nearest .5."""
    return np.round(np.asarray(vals) * 2) / 2
