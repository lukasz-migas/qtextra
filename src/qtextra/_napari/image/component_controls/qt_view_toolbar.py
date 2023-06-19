"""Toolbar."""

from napari.layers.labels._labels_constants import Mode as LabelsMode
from napari.layers.shapes._shapes_constants import Mode as ShapesMode
from napari.utils.events.event import EmitterGroup, Event
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

from qtextra.helpers import make_radio_btn_group, qt_signals_blocked
from qtextra.widgets.qt_mini_toolbar import QtMiniToolbar


class QtViewToolbar(QWidget):
    """Qt toolbars."""

    # dialogs
    _dlg_labels, _dlg_shapes = None, None

    # layers
    _reg_image_layer = None

    def __init__(self, view, viewer, qt_viewer, **kwargs):
        super().__init__(parent=qt_viewer)
        self.view = view
        self.viewer = viewer
        self.qt_viewer = qt_viewer
        # user kwargs
        self.allow_extraction = kwargs.pop("allow_extraction", True)
        self.allow_shapes = kwargs.pop("allow_shapes", True)
        self.allow_masks = kwargs.pop("allow_masks", False)
        self.allow_labels = kwargs.pop("allow_labels", False)
        self.allow_crosshair = kwargs.pop("allow_crosshair", True)

        self.events = EmitterGroup(
            auto_connect=False,
            # shapes
            shapes_open=Event,
            shapes_extract=Event,
            shapes_cancel=Event,
            # labels
            labels_open=Event,
            labels_extract=Event,
            labels_cancel=Event,
            # general
            crosshair=Event,
            selection_off=Event,
            # masks
            mask_extract=Event,
        )
        # connect events
        self.events.labels_cancel.connect(self._on_close_extract_layer)
        self.events.shapes_cancel.connect(self._on_close_extract_layer)
        self.events.selection_off.connect(self._on_close_extract_layer)

        # create instance
        toolbar_left, toolbar_right = QtMiniToolbar(qt_viewer, Qt.Vertical), QtMiniToolbar(qt_viewer, Qt.Vertical)
        self.toolbar_left = toolbar_left
        self.toolbar_right = toolbar_right

        # right-hand toolbar
        # view reset/clear
        self.tools_erase_btn = toolbar_right.insert_qta_tool("erase", tooltip="Clear image", func=viewer.clear_canvas)
        self.tools_erase_btn.hide()
        self.tools_zoomout_btn = toolbar_right.insert_qta_tool("zoom_out", tooltip="Zoom-out", func=viewer.reset_view)
        # view modifiers
        toolbar_right.insert_separator()
        self.tools_clip_btn = toolbar_right.insert_qta_tool(
            "clipboard", tooltip="Copy figure to clipboard", func=self.qt_viewer.clipboard
        )
        self.tools_save_btn = toolbar_right.insert_qta_tool(
            "save", tooltip="Save figure", func=self.qt_viewer.on_save_figure
        )
        # self.tools_settings_btn = toolbar_right.insert_qta_tool(
        #     "settings", tooltip="Settings configuration", checkable=False
        # )
        # self.tools_settings_btn.evt_click.connect(show_image_config)
        self.tools_colorbar_btn = toolbar_right.insert_qta_tool(
            "colorbar", tooltip="Show/hide colorbar", checkable=True
        )
        self.tools_colorbar_btn.connect_to_right_click(self.on_open_colorbar_config)
        self.tools_scalebar_btn = toolbar_right.insert_qta_tool(
            "ruler",
            tooltip="Show/hide scalebar",
            checkable=True,
        )
        self.tools_scalebar_btn.connect_to_right_click(self.on_open_scalebar_config)
        self.tools_text_btn = toolbar_right.insert_qta_tool(
            "text",
            tooltip="Show/hide text label",
            checkable=True,
        )
        self.tools_text_btn.connect_to_right_click(self.on_open_text_config)
        if self.allow_crosshair:
            self.tools_cross_btn = toolbar_right.insert_qta_tool(
                "crosshair",
                tooltip="Show/hide crosshair",
                checkable=True,
            )
            self.tools_cross_btn.connect_to_right_click(self.on_open_crosshair_config)
        self.tools_grid_btn = toolbar_right.insert_qta_tool(
            "grid",
            tooltip="Show/hide grid",
            checkable=True,
        )
        self.registration_btn = toolbar_right.insert_qta_tool(
            "overlap",
            tooltip="Load registered image",
            checkable=False,
            func=self.on_open_registered_image,
        )
        #         self.registration_btn.connect_to_right_click(self.on_open_registered_config)
        self.layers_btn = toolbar_right.insert_qta_tool(
            "layers",
            tooltip="Display layer controls",
            checkable=False,
            func=qt_viewer.on_toggle_controls_dialog,
        )

        # left-side toolbar
        # this branch provides additional tools in the toolbar to allow extraction
        if self.allow_extraction:
            if self.allow_masks:
                self.masks_btn = toolbar_left.insert_qta_tool(
                    "mask",
                    tooltip="Use pre-defined image mask.",
                    checkable=False,
                    func=self.on_open_mask_image,
                )
                self.masks_btn.connect_to_right_click(self.on_open_masks_widget)
            buttons = []
            if self.allow_labels:
                self.tools_new_labels_btn = toolbar_left.insert_qta_tool(
                    "new_labels",
                    tooltip="Paint region of interest using paint brush",
                    checkable=True,
                    func=self.on_open_extract_labels_layer,
                )
                buttons.append(self.tools_new_labels_btn)
            # self.tools_crosshair_btn = toolbar_left.insert_qta_tool(
            #     "target",
            #     tooltip="Cross-hair tool - press anywhere in the image to get underlying data",
            #     set_checkable=True,
            #     func=self.on_open_crosshair_layer,
            # )
            # buttons.append(self.tools_crosshair_btn)
            if self.allow_shapes:
                self.tools_poly_btn = toolbar_left.insert_qta_tool(
                    "polygon",
                    tooltip="Use polygon region of interest",
                    checkable=True,
                    func=lambda _: self.on_open_extract_shapes_layer(ShapesMode.ADD_POLYGON),
                    # func=partial(self.on_open_extract_shapes_layer, ShapesMode.ADD_POLYGON),
                )
                self.tools_ellipse_btn = toolbar_left.insert_qta_tool(
                    "ellipse",
                    tooltip="Use circular region of interest",
                    checkable=True,
                    func=lambda _: self.on_open_extract_shapes_layer(ShapesMode.ADD_ELLIPSE),
                    # func=partial(self.on_open_extract_shapes_layer, ShapesMode.ADD_ELLIPSE),
                )
                self.tools_rectangle_btn = toolbar_left.insert_qta_tool(
                    "rectangle",
                    tooltip="Use rectangular region of interest",
                    checkable=True,
                    func=lambda _: self.on_open_extract_shapes_layer(ShapesMode.ADD_RECTANGLE),
                    # func=partial(self.on_open_extract_shapes_layer, ShapesMode.ADD_RECTANGLE),
                )
                buttons.extend([self.tools_poly_btn, self.tools_ellipse_btn, self.tools_rectangle_btn])
            self.tools_off_btn = toolbar_left.insert_qta_tool(
                "none",
                tooltip="Disable data extraction (default)",
                checkable=True,
                func=self._on_close_extract_layer,
            )
            self.tools_off_btn.setChecked(True)
            buttons.append(self.tools_off_btn)

            if toolbar_left.n_items == 0:
                toolbar_left.setVisible(False)
            if toolbar_right.n_items == 0:
                toolbar_right.setVisible(False)

            _radio_group = make_radio_btn_group(qt_viewer, buttons)

    def connect_toolbar(self):
        """Connect events."""
        self.tools_scalebar_btn.setChecked(self.qt_viewer.viewer.scale_bar.visible)
        self.tools_scalebar_btn.clicked.connect(self._toggle_scale_bar_visible)
        self.qt_viewer.viewer.scale_bar.events.visible.connect(
            lambda x: self.tools_scalebar_btn.setChecked(self.qt_viewer.viewer.scale_bar.visible)
        )

        self.tools_grid_btn.setChecked(self.qt_viewer.viewer.grid_lines.visible)
        self.tools_grid_btn.clicked.connect(self._toggle_grid_lines_visible)
        self.qt_viewer.viewer.grid_lines.events.visible.connect(
            lambda x: self.tools_grid_btn.setChecked(self.qt_viewer.viewer.grid_lines.visible)
        )

        self.tools_colorbar_btn.setChecked(self.qt_viewer.viewer.color_bar.visible)
        self.tools_colorbar_btn.clicked.connect(self._toggle_color_bar_visible)
        self.qt_viewer.viewer.color_bar.events.visible.connect(
            lambda x: self.tools_colorbar_btn.setChecked(self.qt_viewer.viewer.color_bar.visible)
        )

        self.tools_text_btn.setChecked(self.qt_viewer.viewer.text_overlay.visible)
        self.tools_text_btn.clicked.connect(self._toggle_text_visible)
        self.qt_viewer.viewer.text_overlay.events.visible.connect(
            lambda x: self.tools_text_btn.setChecked(self.qt_viewer.viewer.text_overlay.visible)
        )

        if self.allow_crosshair:
            self.tools_cross_btn.setChecked(self.qt_viewer.viewer.cross_hair.visible)
            self.tools_cross_btn.clicked.connect(self._toggle_crosshair_visible)
            self.qt_viewer.viewer.cross_hair.events.visible.connect(
                lambda x: self.tools_cross_btn.setChecked(self.qt_viewer.viewer.cross_hair.visible)
            )

    def _toggle_scale_bar_visible(self, state):
        self.qt_viewer.viewer.scale_bar.visible = state

    def _toggle_grid_lines_visible(self, state):
        self.qt_viewer.viewer.grid_lines.visible = state

    def _toggle_color_bar_visible(self, state):
        self.qt_viewer.viewer.color_bar.visible = state

    def _toggle_text_visible(self, state):
        self.qt_viewer.viewer.text_overlay.visible = state

    def _toggle_crosshair_visible(self, state):
        self.qt_viewer.viewer.cross_hair.visible = state

    def on_open_crosshair_config(self):
        """Open text config."""
        from qtextra._napari.image.component_controls.qt_crosshair_controls import QtCrosshairControls

        dlg = QtCrosshairControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_text_config(self):
        """Open text config."""
        from qtextra._napari.common.component_controls.qt_text_overlay_controls import QtTextOverlayControls

        dlg = QtTextOverlayControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_scalebar_config(self):
        """Open scalebar config."""
        from qtextra._napari.image.component_controls.qt_scalebar_controls import QtScaleBarControls

        dlg = QtScaleBarControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()

    def on_open_colorbar_config(self):
        """Open colorbar config."""
        from qtextra._napari.image.component_controls.qt_colorbar_controls import QtColorBarControls

        dlg = QtColorBarControls(self.viewer, self.qt_viewer)
        dlg.show_left_of_mouse()
