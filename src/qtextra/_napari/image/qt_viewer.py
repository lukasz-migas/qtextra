"""Qt widget that embeds the canvas."""

from napari._qt.containers.qt_layer_list import QtLayerList
from napari._qt.qt_main_window import _QtMainWindow
from napari._qt.widgets.qt_dims import QtDims
from napari._vispy import VispyCamera
from napari._vispy.utils.visual import create_vispy_layer
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout

from qtextra._napari.common.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from qtextra._napari.common.qt_viewer import QtViewerBase
from qtextra._napari.image.component_controls.qt_layer_buttons import QtLayerButtons, QtViewerButtons
from qtextra._napari.image.component_controls.qt_view_toolbar import QtViewToolbar


class QtViewer(QtViewerBase):
    """Qt view for the napari Viewer model."""

    def __init__(
        self,
        view,
        viewer,
        parent=None,
        disable_controls: bool = False,
        add_dims: bool = True,
        add_toolbars: bool = True,
        allow_extraction: bool = True,
        disable_new_layers: bool = False,
        **kwargs,
    ):
        super().__init__(
            view,
            viewer,
            parent=parent,
            disable_controls=disable_controls,
            add_dims=add_dims,
            add_toolbars=add_toolbars,
            allow_extraction=allow_extraction,
            disable_new_layers=disable_new_layers,
            **kwargs,
        )
        _QtMainWindow._instances.append(self)

    @property
    def _qt_viewer(self):
        return self

    def _create_canvas(self):
        """Create canvas."""
        super()._create_canvas()
        self.canvas.events.draw.connect(self.dims.enable_play)
        self.viewer.events.theme.connect(self.canvas._on_theme_change)

    def _create_widgets(self, **kwargs):
        """Create ui widgets."""
        # dimensions widget
        self.dims = QtDims(self.viewer.dims)
        # widget showing layer controls
        self.controls = QtLayerControlsContainer(self.viewer)
        # widget showing current layers
        self.layers = QtLayerList(self.viewer.layers)
        # widget showing layer buttons (e.g. add new shape)
        self.layerButtons = QtLayerButtons(self.viewer, **kwargs)
        # viewer buttons to control 2d/3d, grid, transpose, etc
        self.viewerButtons = QtViewerButtons(self.viewer, self)
        # toolbar
        self.viewerToolbar = QtViewToolbar(self.view, self.viewer, self, **kwargs)

    def _set_layout(self, add_dims: bool, add_toolbars: bool, **kwargs):
        # set in main canvas
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.canvas.native, stretch=True)
        image_layout.setContentsMargins(0, 2, 0, 2)
        if add_dims:
            image_layout.addWidget(self.dims)
            image_layout.setSpacing(0)
        else:
            image_layout.setSpacing(0)
            image_layout.setContentsMargins(0, 0, 0, 0)

        # view widget
        main_layout = QHBoxLayout()
        main_layout.setSpacing(1)
        main_layout.addLayout(image_layout)
        main_layout.setContentsMargins(2, 2, 2, 2)
        if add_toolbars:
            main_layout.insertWidget(0, self.viewerToolbar.toolbar_left)
            main_layout.addWidget(self.viewerToolbar.toolbar_right)
        else:
            self.viewerToolbar.setVisible(False)
            self.viewerToolbar.toolbar_left.setVisible(False)
            self.viewerToolbar.toolbar_right.setVisible(False)
            main_layout.setSpacing(0)

        self.setLayout(main_layout)

    def _set_events(self):
        # bind events
        self.viewer.layers.selection.events.active.connect(self._on_active_change)
        self.viewer.camera.events.interactive.connect(self._on_interactive)
        self.viewer.cursor.events.style.connect(self._on_cursor)
        self.viewer.cursor.events.size.connect(self._on_cursor)
        self.viewer.camera.events.zoom.connect(self._on_cursor)
        self.viewer.layers.events.reordered.connect(self._reorder_layers)
        self.viewer.layers.events.inserted.connect(self._on_add_layer_change)
        self.viewer.layers.events.removed.connect(self._remove_layer)
        # stop any animations whenever the layers change
        self.viewer.events.layers_change.connect(lambda x: self.dims.stop())

    def _set_view(self):
        """Set view."""
        self.view = self.canvas.central_widget.add_view()

    def _set_camera(self):
        self.camera = VispyCamera(self.view, self.viewer.camera, self.viewer.dims)
        self.canvas.connect(self.camera.on_draw)

    def _post_init(self):
        """Complete initialization with post-init events."""
        self.viewerToolbar.connect_toolbar()

    @property
    def color_bar(self):
        """Grid lines."""
        return self.overlay_to_visual["color_bar"]

    @property
    def scale_bar(self):
        """Grid lines."""
        return self.overlay_to_visual["scale_bar"]

    @property
    def axes(self):
        """Grid lines."""
        return self.overlay_to_visual["axes"]

    def _add_visuals(self) -> None:
        """Add visuals for axes, scale bar."""
        for layer in self.viewer.layers:
            self._add_layer(layer)
        for overlay in self.viewer._overlays.values():
            self._add_overlay(overlay)
        # add scalebar
        # self.canvas.events.resize.connect(self.scale_bar._on_position_change)

        # add colorbar
        # self.color_bar = VispyColorbarOverlay(self.viewer, parent=self.view, order=1e6 + 3)
        # self.canvas.events.resize.connect(self.color_bar._on_position_change)

        # add label
        # self.text_overlay = VispyTextOverlay(self.viewer, parent=self.view, order=1e6 + 5)

        # self.interaction_box_visual = VispyTransformBoxOverlay(self.viewer, parent=self.view.scene, order=1e6 + 4)
        # self.interaction_box_mousebindings = TransformBoxOverlay(self.viewer, self.interaction_box_visual)

    def _add_layer(self, layer):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        layer : napari.layers.Layer
            Layer to be added.
        """
        vispy_layer = create_vispy_layer(layer)
        vispy_layer.node.parent = self.view.scene
        # ensure correct canvas blending
        layer.events.visible.connect(self._reorder_layers)
        self.layer_to_visual[layer] = vispy_layer
        self._reorder_layers()

    def on_open_controls_dialog(self, event=None):
        """Open dialog responsible for layer settings."""
        from qtextra._napari.image.component_controls.qt_layers_dialog import DialogNapariControls

        if self._disable_controls:
            return

        if self._layers_controls_dialog is None:
            self._layers_controls_dialog = DialogNapariControls(self)
            # self._layers_controls_dialog.set_on_widget(self, 0, 0)
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
        # if the viewer.QtDims object is playing an axis, we need to terminate
        # the AnimationThread before close, otherwise it will cause a segFault
        # or Abort trap. (calling stop() when no animation is occurring is also
        # not a problem)
        self.dims.stop()
        self.canvas.native.deleteLater()
        event.accept()
