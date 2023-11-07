"""Qt widget that embeds the canvas."""
from napari._qt.containers.qt_layer_list import QtLayerList
from napari._qt.widgets.qt_dims import QtDims
from napari._vispy import VispyCamera
from napari._vispy.overlays.axes import VispyAxesOverlay
from napari._vispy.overlays.interaction_box import VispyTransformBoxOverlay
from napari._vispy.overlays.scale_bar import VispyScaleBarOverlay
from napari._vispy.overlays.text import VispyTextOverlay
from napari.components.overlays.interaction_box import TransformBoxOverlay
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout

try:
    from napari_plot._vispy.overlays.grid_lines import VispyGridLinesVisual
except ImportError:
    VispyGridLinesVisual = None

from qtextra._napari.common.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
from qtextra._napari.common.qt_viewer import QtViewerBase
from qtextra._napari.image._vispy.utils import create_vispy_visual
from qtextra._napari.common._vispy.overlays.color_bar_mpl import VispyColorbarOverlay
from qtextra._napari.common._vispy.overlays.crosshair import VispyCrosshairVisual
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
            **kwargs,
        )

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
        self.layerButtons = QtLayerButtons(self.viewer)
        # viewer buttons to control 2d/3d, grid, transpose, etc
        self.viewerButtons = QtViewerButtons(self.viewer, self)
        # toolbar
        self.viewerToolbar = QtViewToolbar(self.view, self.viewer, self, **kwargs)

    def _set_layout(self, add_dims: bool, add_toolbars: bool, **kwargs):
        # set in main canvas
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.canvas.native, stretch=True)
        if add_dims:
            image_layout.addWidget(self.dims)
            image_layout.setSpacing(10)
        else:
            image_layout.setSpacing(0)
            image_layout.setContentsMargins(0, 0, 0, 0)

        # view widget
        main_layout = QHBoxLayout()
        main_layout.addLayout(image_layout)

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

    def _add_visuals(self) -> None:
        """Add visuals for axes, scale bar."""
        # add gridlines
        self.grid_lines = VispyGridLinesVisual(self.viewer, parent=self.view, order=1e6)

        # add axes
        self.axes = VispyAxesOverlay(self.viewer, parent=self.view.scene, order=1e6 + 1)

        # add scalebar
        self.scale_bar = VispyScaleBarOverlay(self.viewer, parent=self.view, order=1e6 + 2)
        self.canvas.events.resize.connect(self.scale_bar._on_position_change)

        # add colorbar
        self.color_bar = VispyColorbarOverlay(self.viewer, parent=self.view, order=1e6 + 3)
        self.canvas.events.resize.connect(self.color_bar._on_position_change)

        # add axes
        self.cross_hair = VispyCrosshairVisual(self.viewer, parent=self.view.scene, order=1e6 + 4)

        # add label
        self.text_overlay = VispyTextOverlay(self.viewer, parent=self.view, order=1e6 + 5)

        self.interaction_box_visual = VispyTransformBoxOverlay(self.viewer, parent=self.view.scene, order=1e6 + 4)
        self.interaction_box_mousebindings = TransformBoxOverlay(self.viewer, self.interaction_box_visual)

    def _add_layer(self, layer):
        """When a layer is added, set its parent and order.

        Parameters
        ----------
        layer : napari.layers.Layer
            Layer to be added.
        """
        vispy_layer = create_vispy_visual(layer)
        vispy_layer.node.parent = self.view.scene
        vispy_layer.order = len(self.viewer.layers) - 1
        self.layer_to_visual[layer] = vispy_layer

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
