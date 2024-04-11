"""Toolbar."""

from napari_plot.components.dragtool import DragMode
from qtpy.QtCore import Qt

from qtextra.helpers import make_radio_btn_group
from qtextra.widgets.qt_mini_toolbar import QtMiniToolbar


class QtViewLeftToolbar(QtMiniToolbar):
    """Mini toolbar."""

    def __init__(self, view, viewer, qt_viewer, **kwargs):
        super().__init__(parent=qt_viewer, orientation=Qt.Orientation.Vertical)
        self.view = view
        self.viewer = viewer
        self.qt_viewer = qt_viewer
        self.allow_tools = kwargs.get("allow_tools", False)

        if self.allow_tools:
            self.tools_select_lasso = self.insert_qta_tool(
                "lasso",
                tooltip="Click to select data points using lasso region of interest.",
                checkable=True,
                func=lambda _: setattr(self.viewer.drag_tool, "active", DragMode.LASSO),
            )
            self.tools_select_poly = self.insert_qta_tool(
                "polygon",
                tooltip="Click to select data points using lasso region of interest.",
                checkable=True,
                func=lambda _: setattr(self.viewer.drag_tool, "active", DragMode.POLYGON),
            )
            self.tools_select_box = self.insert_qta_tool(
                "rectangle",
                tooltip="Click to select data points using box shaped region of interest.",
                checkable=True,
                func=lambda _: setattr(self.viewer.drag_tool, "active", DragMode.BOX_SELECT),
            )
            self.tools_zoom = self.insert_qta_tool(
                "zoom",
                tooltip="Click here to enable default zoom interaction",
                checkable=True,
                func=lambda _: setattr(self.viewer.drag_tool, "active", DragMode.BOX),
            )
            self.tools_zoom.setChecked(True)
            _radio_group = make_radio_btn_group(
                qt_viewer,
                [self.tools_select_lasso, self.tools_select_poly, self.tools_select_box, self.tools_zoom],
            )
            self.viewer.drag_tool.events.active.connect(self._on_active_tool_change)
        self.zoom_btn = self.insert_qta_tool(
            "marker",
            tooltip="Zoom-in on region of interest",
            checkable=False,
            func=self.on_open_zoom,
        )
        if self.n_items == 0:
            self.setVisible(False)

    def connect_toolbar(self):
        """Connect events."""

    def _on_active_tool_change(self, event):
        """Change currently active tool."""
        if not self.allow_tools:
            return

        tool = event.value
        if tool == DragMode.BOX:
            self.tools_zoom.setChecked(True)
        elif tool == DragMode.BOX_SELECT:
            self.tools_select_box.setChecked(True)
        elif tool == DragMode.POLYGON:
            self.tools_select_poly.setChecked(True)
        elif tool == DragMode.LASSO:
            self.tools_select_lasso.setChecked(True)

    def on_open_zoom(self):
        """Open zoom dialog."""
        from qtextra._napari.common.widgets.zoom_widget import XZoomPopup

        dlg = XZoomPopup(self.viewer, self)
        dlg.show_right_of_mouse()


class QtViewRightToolbar(QtMiniToolbar):
    """Qt toolbars."""

    # dialogs
    _dlg_shapes, _dlg_region = None, None

    def __init__(self, view, viewer, qt_viewer, **kwargs):
        super().__init__(parent=qt_viewer, orientation=Qt.Orientation.Vertical)
        self.view = view
        self.viewer = viewer
        self.qt_viewer = qt_viewer

        # view reset/clear
        self.tools_erase_btn = self.insert_qta_tool("erase", tooltip="Clear image", func=viewer.clear_canvas)
        self.tools_erase_btn.hide()
        self.tools_zoomout_btn = self.insert_qta_tool("zoom_out", tooltip="Zoom-out", func=viewer.reset_view)
        self.tools_zoomout_btn.connect_to_right_click(self.on_open_camera_config)
        # view modifiers
        self.insert_separator()
        self.tools_clip_btn = self.insert_qta_tool(
            "clipboard",
            tooltip="Copy figure to clipboard",
            func=self.qt_viewer.clipboard,
            func_menu=self.on_open_save_figure,
        )
        self.tools_save_btn = self.insert_qta_tool(
            "save", tooltip="Save figure", func=self.qt_viewer.on_save_figure, func_menu=self.on_open_save_figure
        )
        self.tools_axes_btn = self.insert_qta_tool(
            "axes_label",
            tooltip="Show axes controls",
            checkable=True,
            check=self.viewer.axis.visible,
            func=self._toggle_axes_visible,
            func_menu=self.on_open_axes_config,
        )
        self.tools_text_btn = self.insert_qta_tool(
            "text",
            tooltip="Show/hide text label",
            checkable=True,
            check=self.viewer.text_overlay.visible,
            func=self._toggle_text_visible,
            func_menu=self.on_open_text_config,
        )
        self.tools_grid_btn = self.insert_qta_tool(
            "grid",
            tooltip="Show/hide grid",
            checkable=True,
            check=self.viewer.grid_lines.visible,
            func=self._toggle_grid_lines_visible,
        )
        self.layers_btn = self.insert_qta_tool(
            "layers",
            tooltip="Display layer controls",
            checkable=False,
            func=qt_viewer.on_toggle_controls_dialog,
        )

        if self.n_items == 0:
            self.setVisible(False)

    def connect_toolbar(self):
        """Connect events."""
        self.qt_viewer.viewer.grid_lines.events.visible.connect(
            lambda x: self.tools_grid_btn.setChecked(self.qt_viewer.viewer.grid_lines.visible)
        )
        self.qt_viewer.viewer.text_overlay.events.visible.connect(
            lambda x: self.tools_text_btn.setChecked(self.qt_viewer.viewer.text_overlay.visible)
        )
        self.qt_viewer.viewer.axis.events.visible.connect(
            lambda x: self.tools_axes_btn.setChecked(self.qt_viewer.viewer.axis.visible)
        )

    def _toggle_grid_lines_visible(self, state):
        self.qt_viewer.viewer.grid_lines.visible = state

    def _toggle_text_visible(self, state):
        self.qt_viewer.viewer.text_overlay.visible = state

    def on_open_text_config(self):
        """Open text config."""
        from qtextra._napari.common.component_controls.qt_text_overlay_controls import QtTextOverlayControls

        dlg = QtTextOverlayControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def _toggle_axes_visible(self, state):
        self.qt_viewer.viewer.axis.visible = state

    def on_open_axes_config(self):
        """Open scalebar config."""
        from qtextra._napari.line.component_controls.qt_axis_controls import QtAxisControls

        dlg = QtAxisControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_camera_config(self):
        """Open scalebar config."""
        from qtextra._napari.line.component_controls.qt_camera_controls import QtCameraControls

        dlg = QtCameraControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_save_figure(self) -> None:
        """Show scale bar controls for the viewer."""
        from qtextra._napari.common.widgets.screenshot_dialog import QtScreenshotDialog

        dlg = QtScreenshotDialog(self.view, self)
        dlg.show_above_widget(self.tools_save_btn)
