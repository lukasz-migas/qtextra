"""Various toolbars that are used throughout the app."""
from __future__ import annotations

import typing as ty

from qtpy.QtWidgets import QWidget

import qtextra.helpers as hp

if ty.TYPE_CHECKING:
    from napari.layers import Image

    from qtextra._napari.image.wrapper import NapariImageView
    from qtextra._napari.line.wrapper import NapariLineView


class ImageViewMixin:
    """Mixin class."""

    view_image: NapariImageView
    image_layer: Image | None = None

    def on_plot_image_outline(self, value: bool):
        """Plot outline."""

    def _make_image_view(
        self,
        widget: QWidget,
        disable_controls=False,
        add_toolbars=True,
        allow_extraction=True,
            disable_new_layers: bool = False,
        **kwargs,
    ) -> NapariImageView:
        """Make image view."""
        from qtextra._napari.image.wrapper import NapariImageView

        return NapariImageView(
            widget,
            main_parent=self,
            disable_controls=disable_controls,
            add_toolbars=add_toolbars,
            allow_extraction=allow_extraction,
            disable_new_layers=disable_new_layers,
            **kwargs,
        )


class LineViewMixin:
    """Mixin class."""

    def _make_line_view(
        self,
        widget: QWidget,
        disable_controls=False,
        add_toolbars=True,
        allow_extraction=True,
        allow_tools=False,
        x_label: str = "",
        y_label: str = "",
        lock_to_bottom: bool = False,
        **kwargs,
    ) -> NapariLineView:
        """Make line view."""
        from qtextra._napari.line.wrapper import NapariLineView

        return NapariLineView(
            widget,
            main_parent=self,
            disable_controls=disable_controls,
            add_toolbars=add_toolbars,
            allow_extraction=allow_extraction,
            allow_tools=allow_tools,
            x_label=x_label,
            y_label=y_label,
            lock_to_bottom=lock_to_bottom,
            **kwargs,
        )

    def on_yaxis_zoom(self, viewer, event):
        """Zoom y-axis of the current tab."""
        yield  # ignore press event
        while event.type == "mouse_move":
            yield
        hp.call_later(self, viewer.reset_current_y_view, 50)

    def on_yaxis_zoom_wheel(self, viewer, event):
        """Zoom y-axis of the current tab."""
        hp.call_later(self, viewer.reset_current_y_view, 200)
