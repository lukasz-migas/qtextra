"""Dialog."""

from __future__ import annotations

import typing as ty
from weakref import ref

from loguru import logger
from napari.utils.events import Event, EventEmitter, disconnect_events
from qtpy.QtCore import Qt, Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_labels_controls import QtLabelsControls
from qtextra._napari.common.layer_controls.qt_shapes_controls import QtShapesControls
from qtextra.widgets.qt_dialog import QtFramelessTool

if ty.TYPE_CHECKING:
    from napari.layers import Labels, Shapes
    from napari_plot.layers import Region

    from qtextra._napari.image import NapariImageView


class ImageMaskROIExtractPopupBase(QtFramelessTool):
    """Popup tool to perform some extraction task."""

    HIDE_WHEN_CLOSE = False

    def __init__(
        self,
        parent: QWidget | None,
        viewer: NapariImageView,
        layer: ty.Union[Labels, Region, Shapes],
        msg: str = "When you have finished selecting region(s) of interest, please click on OK.",
        n_max: int = 1,
        auto_close: bool = False,
    ):
        self.ref_viewer: ty.Callable[[None], NapariImageView] = ref(viewer)
        self.layer = layer
        self.msg = msg
        self.n_max = n_max
        self.auto_close = auto_close
        super().__init__(parent)
        viewer.viewer.events.help.connect(self._on_help_changed)
        viewer.viewer.layers.events.removed.connect(self._on_layer_removed)
        viewer.viewer.layers.selection.events.active.connect(self._on_layer_active)

    def events(self) -> EventEmitter | None:
        """Events."""
        viewer: NapariImageView = self.ref_viewer()  # type: ignore[assignment]
        if hasattr(viewer.widget.viewerToolbar, "events"):
            return viewer.widget.viewerToolbar.events  # type: ignore[union-attr]
        return None

    def _on_teardown(self) -> None:
        """Clean-up."""
        viewer: NapariImageView = self.ref_viewer()  # type: ignore[assignment]
        disconnect_events(viewer.viewer.events, self)
        disconnect_events(viewer.viewer.layers.events, self)
        disconnect_events(viewer.viewer.layers.selection.events, self)

    def _on_layer_removed(self, event: Event) -> None:
        """Indicate if layer has been deleted."""
        layer = event.value
        events = self.events()
        if layer == self.layer and events and hasattr(events, "selection_off"):
            events.selection_off()
            logger.trace(f"Selection off from layer '{layer.name}'.")
            QtFramelessTool.close(self)

    def _on_help_changed(self, event: Event) -> None:
        """Update help message on status bar."""
        text = event.value
        self._help_sep.setVisible(text != "")
        self._help_msg.setText(text)
        self.adjustSize()

    def on_select(self) -> None:
        """Select layer."""
        viewer: NapariImageView = self.ref_viewer()  # type: ignore[assignment]
        viewer.widget.viewer.layers.selection.clear()
        viewer.widget.viewer.layers.selection.active = self.layer

    def _on_layer_active(self, event: Event) -> None:
        """Indicate if layer has been deselected."""
        active_layer = event.value
        self.layer.editable = active_layer == self.layer

    def _make_layer_controls(self) -> QWidget:
        """Actually make layer controls."""
        raise NotImplementedError("Must implement method")

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Make panel."""
        layer_controls = self._make_layer_controls()

        # accept/cancel buttons
        label = hp.make_label(self, self.msg, wrap=True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._help_sep = hp.make_h_line(self)
        self._help_sep.setVisible(False)
        self._help_msg = hp.make_label(self, "", wrap=True, object_name="ViewerStatusBar")

        select_btn = hp.make_btn(self, "Activate")
        select_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_btn.clicked.connect(self.on_select)
        ok_btn = hp.make_btn(self, "OK")
        ok_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_btn.clicked.connect(self.on_ok)
        cancel_btn = hp.make_btn(self, "Cancel")
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_btn.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.addSpacing(2)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(self._make_close_handle("Edit mask")[1])
        layout.addWidget(layer_controls, stretch=True)
        layout.addWidget(hp.make_h_line(self))
        layout.addWidget(label)
        layout.addLayout(hp.make_h_layout(select_btn, ok_btn, cancel_btn, spacing=2, margin=2))
        layout.addWidget(self._help_sep)
        layout.addWidget(self._help_msg)
        return layout

    def on_ok(self, _event: ty.Any = None) -> None:
        """Accept function."""
        raise NotImplementedError("Must implement method")

    def keyPressEvent(self, event):
        """Called whenever a key is pressed.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.ref_viewer().widget.canvas._backend._keyEvent(self.ref_viewer().widget.canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event):
        """Called whenever a key is released.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        self.ref_viewer().widget.canvas._backend._keyEvent(self.ref_viewer().widget.canvas.events.key_release, event)
        event.accept()


class ImageLabelsROIExtractPopup(ImageMaskROIExtractPopupBase):
    """Popup tool to perform some extraction task."""

    evt_update = Signal(object)

    def __init__(
        self,
        parent: QWidget | None,
        view: NapariImageView,
        layer: Labels,
        msg: str = "When you have finished selecting region(s) of interest, please click on the <b>OK</b> button.",
        n_max: int = 1,
        auto_close: bool = False,
    ):
        super().__init__(parent, view, layer, msg, n_max, auto_close)
        self.setMaximumWidth(400)

    def on_ok(self, _event: ty.Any = None) -> None:
        """Accept function."""
        events = self.events()
        if events and hasattr(events, "labels_extract"):
            events.labels_extract(layer=self.layer)
            logger.trace(f"Labels extracted from layer '{self.layer.name}'.")
        self.evt_update.emit(self.layer)
        if self.auto_close:
            self.close()

    def _on_teardown(self) -> None:
        """Teardown."""
        super()._on_teardown()
        events = self.events()
        if events and hasattr(events, "labels_cancel"):
            events.labels_cancel()

    def _make_layer_controls(self) -> QtLabelsControls:
        """Actually make layer controls."""
        return QtLabelsControls(self.layer)


class ImageShapesROIExtractPopup(ImageMaskROIExtractPopupBase):
    """Popup tool to perform some extraction task."""

    def __init__(
        self,
        parent: QWidget | None,
        view: NapariImageView,
        layer: Labels,
        msg: str = "When you have finished selecting region(s) of interest, please click on the <b>OK</b> button.",
        n_max: int = 1,
        auto_close: bool = False,
    ):
        super().__init__(parent, view, layer, msg, n_max, auto_close)
        self.setMaximumWidth(400)

    def on_ok(self, _event: ty.Any = None) -> None:
        """Accept function."""
        events = self.events()
        if len(self.layer.data) == 0:
            hp.warn_pretty(self, "No regions selected - please annotate image to continue.", "Warning")
            return
        if events and hasattr(events, "shapes_extract"):
            events.shapes_extract(layer=self.layer)
        if self.auto_close:
            self.close()

    def _on_teardown(self) -> None:
        """Teardown."""
        super()._on_teardown()
        events = self.events()
        if events and hasattr(events, "shapes_cancel"):
            events.shapes_cancel()

    def _make_layer_controls(self) -> QtShapesControls:
        """Actually make layer controls."""
        return QtShapesControls(self.layer)
