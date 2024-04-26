"""Add napari based viewer."""

from __future__ import annotations

import typing as ty

import numpy as np
from koyo.image import clip_hotspots
from koyo.secret import get_short_hash
from napari.layers import Image, Labels, Points, Shapes
from qtpy.QtCore import QMutex, QMutexLocker, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QWidget

from qtextra._napari.common.components.overlays.color_bar import ColorBarItem
from qtextra._napari.common.wrapper import ViewerBase
from qtextra._napari.image.components.viewer_model import ViewerModel as Viewer
from qtextra._napari.image.qt_viewer import QtViewer

MUTEX = QMutex()
IMAGE_NAME, PAINT_NAME, MASK_NAME, LABELS_NAME, SHAPES_NAME = (
    "Image",
    "Paint",
    "Mask",
    "Extract mask",
    "Shape mask",
)


class NapariImageView(ViewerBase):
    """Napari-based image viewer."""

    PLOT_TYPE = "image"

    def __init__(self, parent: QWidget | None = None, **kwargs: ty.Any):
        self.parent = parent
        self.main_parent = kwargs.pop("main_parent", None)
        self.PLOT_ID = get_short_hash()

        # create instance of viewer
        self.viewer: Viewer = Viewer(**kwargs)
        # create instance of qt widget
        self.widget: QtViewer = QtViewer(
            self,
            self.viewer,
            parent=parent,
            disable_controls=kwargs.pop("disable_controls", False),
            add_dims=kwargs.pop("add_dims", True),
            add_toolbars=kwargs.pop("add_toolbars", True),
            allow_extraction=kwargs.pop("allow_extraction", True),
            disable_new_layers=kwargs.pop("disable_new_layers", False),
            **kwargs,
        )
        self.toolbar = self.widget.viewerToolbar

        # add few layers
        self.image_layer = None
        self.paint_layer = None
        self.extract_layer = None
        self.shape_layer = None
        self.mask_layer = None

        # connect events
        self.viewer.events.clear_canvas.connect(self._clear)
        self.viewer.layers.events.removed.connect(self._on_remove_layer)

    def _on_remove_layer(self, _evt=None):
        """Indicate if layer has been deleted."""
        layer = _evt.value
        if self.image_layer is not None and layer.name == self.image_layer.name:
            self.image_layer = None
        if self.paint_layer is not None and layer.name == self.paint_layer.name:
            self.paint_layer = None
        if self.extract_layer is not None and layer.name == self.extract_layer.name:
            self.extract_layer = None
        if self.shape_layer is not None and layer.name == self.shape_layer.name:
            self.shape_layer = None

    def has_plot(self):
        """Flag to indicate whether there is anything plotted."""
        return self.image_layer is not None

    def _clear(self, _evt=None):
        """Clear canvas."""
        self.image_layer, self.paint_layer, self.extract_layer, self.shape_layer = None, None, None, None
        self.mask_layer = None

    @Slot(np.ndarray)  # type: ignore[misc]
    def plot(
        self,
        array: np.ndarray,
        name: str = IMAGE_NAME,
        colormap: str | None = None,
        interpolation: str = "nearest",
        clip: bool = True,
        **kwargs: ty.Any,
    ) -> Image:
        """Update data."""
        if clip:
            array = clip_hotspots(array)

        if self.image_layer is None:
            self.image_layer: Image = self.viewer.add_image(  # type: ignore[no-untyped-call]
                array,
                name=name,
                colormap=colormap,
                **kwargs,
            )
            self.image_layer.interpolation2d = interpolation  # type: ignore[attr-defined]
            self.image_layer._keep_auto_contrast = True  # type: ignore[attr-defined]
        else:
            # update image data
            self.image_layer.data = array
            if colormap is not None:
                self.image_layer.colormap = colormap
            # update contrast limits
            self.update_image_contrast_limits(self.image_layer)
        return self.image_layer

    def add_image(
        self,
        array: np.ndarray,
        name: str = IMAGE_NAME,
        colormap: str | None = None,
        blending: str = "additive",
        contrast_limits: tuple[float, float] | None = None,
        interpolation: str = "nearest",
        keep_auto_contrast: bool = False,
        **kwargs: ty.Any,
    ) -> Image:
        """Add image layer."""
        layer: ty.Optional[Image] = self.try_reuse(name, Image)
        if layer:
            layer.data = array
            if contrast_limits is not None:
                layer.contrast_limits_range = contrast_limits
                layer.contrast_limits = contrast_limits
            else:
                layer.contrast_limits_range = layer._calc_data_range()
                layer._contrast_limits = tuple(layer.contrast_limits_range)
                layer.contrast_limits = layer._contrast_limits
            layer._keep_auto_contrast = keep_auto_contrast
            layer.blending = blending
            if colormap is not None:
                layer.colormap = colormap
            layer.visible = True
            layer.affine = kwargs.pop("affine", layer.affine)
            layer.translate = kwargs.pop("translate", (0.0, 0.0))
            layer.metadata = kwargs.pop("metadata", layer.metadata)
        else:
            layer = self.viewer.add_image(  # type: ignore[no-untyped-call]
                data=array,
                name=name,
                blending=blending,
                colormap=colormap,
                interpolation2d=interpolation,
                contrast_limits=contrast_limits,
                **kwargs,
            )
            layer._keep_auto_contrast = keep_auto_contrast
        return layer

    def plot_rgb(self, array: np.ndarray, name: str = IMAGE_NAME, **kwargs: ty.Any) -> Image:
        """Full replot of the data."""
        # array = np.nan_to_num(array)
        if self.image_layer is not None:
            if array.ndim != self.image_layer.data.ndim:
                self.viewer.layers.selection.select_only(self.image_layer)
                self.viewer.layers.remove_selected()
        return self.plot(array, name=name, **kwargs)

    def quick_update(self, array: np.ndarray) -> None:
        """Quickly update image data."""
        if self.image_layer is None:
            self.plot(array)
        else:
            array = np.nan_to_num(array)
            with QMutexLocker(MUTEX):
                # update image data
                self.image_layer.data = array
                # update contrast limits
                # self.image_layer._contrast_limits = tuple(self.image_layer.contrast_limits_range)
                # self.image_layer.contrast_limits = self.image_layer._contrast_limits
                self.image_layer.contrast_limits_range = self.image_layer._calc_data_range()

    def set_colorbar_data(self, data: ty.Tuple[ColorBarItem, ...]) -> None:
        """Set colorbar data."""
        self.viewer.color_bar.data = ()  # clear to avoid ValueError # FIXME: this is not desired
        self.viewer.color_bar.data = data

    def add_image_mask(
        self,
        array: np.ndarray,
        name: str = "Masks",
        colors: np.ndarray | None = None,
        opacity: float = 0.75,
        editable: bool = False,
    ) -> Labels:
        """Add image labels layer."""
        layer = self.try_reuse(name, Labels)
        if layer is None:
            layer = self.viewer.add_labels(
                array,
                name=name,
                color=colors,
                opacity=opacity,
            )
        else:
            layer.data = array
            layer.color = colors
        layer.visible = True
        layer.editable = editable
        return layer

    def add_shapes_layer(self, data: ty.List[np.ndarray], shape_type: ty.List[str], name: str) -> Shapes:
        """Add new shapes layer with specified shapes."""
        layer = self.viewer.add_shapes(
            data=data,
            shape_type=shape_type,
            ndim=max(self.viewer.dims.ndim, 2),
            scale=self.viewer.layers.extent.step,
            name=name,
        )
        return layer

    def remove_image_mask(self, name: str = "Masks") -> None:
        """Remove image labels layer."""
        self.remove_layer(name)

    def activate_extract_layer(self) -> None:
        """Activate extraction layer in case it was deactivated during plotting."""
        if self.shape_layer is not None:
            self.add_extract_shapes_layer()
        elif self.extract_layer is not None:
            self.add_extract_labels_layer()

    def add_paint_mask(self) -> None:
        """Add new paint layer if one is not present yet."""
        if self.paint_layer is None:
            self.viewer.new_labels_for_image([self.image_layer], PAINT_NAME)
            self.paint_layer = self.viewer.layers[PAINT_NAME]
        self.viewer.layers.selection.add(self.paint_layer)

    def add_extract_labels_layer(self) -> Labels:
        """Add new (or reuse existing) layer to enable data extraction."""
        if self.extract_layer is None:
            self.viewer.new_labels_for_image([self.image_layer], LABELS_NAME)
            self.extract_layer = self.viewer.layers[LABELS_NAME]
        self.viewer.layers.selection.add(self.extract_layer)
        return self.extract_layer

    def add_extract_shapes_layer(self) -> Shapes:
        """Add new (or reuse existing) layer to enable data extraction."""
        if self.shape_layer is None:
            self.viewer.add_shapes(
                ndim=max(self.viewer.dims.ndim, 2),
                scale=self.viewer.layers.extent_for([self.image_layer]).step,
                name=SHAPES_NAME,
            )
            self.shape_layer = self.viewer.layers[SHAPES_NAME]
        self.viewer.layers.selection.add(self.shape_layer)
        return self.shape_layer

    def add_points_layer(
        self,
        text: ty.List[str],
        position: ty.List,
        text_schema: str = "{label}",
        text_size: int = 12,
        text_color: str = "#FFFFFF",
        translation: ty.Tuple = (0, 0),
        text_anchor: str = "upper_left",
        name: str = "Text",
        size: float = 1,
    ) -> Points:
        """Add text layer.

        In Napari, there is no specific text layer, but the points layer can be used display labels
        """
        data = np.asarray(position)
        # assert len(data) == len(text), "The number of text labels should match that of the number of points."

        text_schema_dict = {
            "text": text_schema,
            "size": text_size,
            "color": text_color,
            "translation": np.array(translation),
            "anchor": text_anchor,
        }
        properties = {"label": text}

        layer = self.try_reuse(name, Points)
        if layer is not None:
            layer.data = data
            layer.text = text_schema
            layer.properties = properties
        else:
            layer = self.viewer.add_points(
                data,
                size=size,  # size of the point(s)
                text=text_schema_dict,
                properties=properties,
                name=name,
            )
        return layer

    def add_text_label(
        self,
        text: ty.List[str],
        position: ty.List,
        text_schema: str = "{label}",
        text_size: int = 12,
        text_color: str = "#FFFFFF",
        translation: ty.Tuple = (0, 0),
        text_anchor: str = "upper_left",
        name: str = "Text",
    ) -> Points:
        """Add text layer.

        In Napari, there is no specific text layer, but the points layer can be used display labels
        """
        data = np.asarray(position)
        assert len(data) == len(text), "The number of text labels should match that of the number of points."

        text_schema_dict = {
            "text": text_schema,
            "size": text_size,
            "color": text_color,
            "translation": np.array(translation),
            "anchor": text_anchor,
        }
        properties = {"label": text}

        layer = self.try_reuse(name, Points)
        if layer is not None:
            layer.data = data
            layer.text = text_schema
            layer.properties = properties
        else:
            layer = self.viewer.add_points(
                data,
                size=0,  # size if the point(s)
                text=text_schema_dict,
                properties=properties,
                name=name,
            )
        return layer


if __name__ == "__main__":  # pragma: no cover

    def _main() -> None:
        import sys

        from skimage import data

        from qtextra.config.theme import THEMES
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qframe

        def _on_btn():
            """Button action."""
            # layer.translate = np.random.randint(0, 100, (2,))
            # viewer.viewer.text_overlay.text = viewer.viewer.text_overlay.text + "T"
            # viewer.viewer.text_overlay.position = random.choice(list(Position))
            # viewer.viewer.text_overlay.font_size += 1

        def _accept(event):
            wrapper.viewer.cross_hair.position = event.position

        app, frame, ha = qframe()
        frame.setMinimumSize(600, 600)
        wrapper = NapariImageView(frame)

        wrapper.plot(data.astronaut(), clip=False)
        # layer.mode = "transform"
        #         layer.events.crosshair.connect(_accept)
        #         viewer.viewer.cross_hair.visible = True

        # points = viewer.viewer.add_points(
        #     np.array([0, 0]),
        #     size=0,
        #     text={
        #         "text": "IM: {label}",
        #         "size": 12,
        #         "color": "white",
        #         "translation": np.array([0, 0]),
        #         "anchor": "upper_left",
        #     },
        #     properties={"label": ["TEST"]},
        # )

        THEMES.set_theme_stylesheet(wrapper.widget)

        btn = make_btn(frame, "Click me")
        btn.clicked.connect(_on_btn)

        # ha.addLayout(va)
        ha.addWidget(wrapper.widget, stretch=True)
        ha.addWidget(btn)
        frame.show()
        sys.exit(app.exec_())

    _main()
