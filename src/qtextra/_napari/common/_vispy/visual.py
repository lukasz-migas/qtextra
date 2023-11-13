"""Create overlays."""
from napari._vispy.utils.visual import create_vispy_overlay, overlay_to_visual

from qtextra._napari.common._vispy.overlays.color_bar_mpl import VispyColorbarOverlay
from qtextra._napari.common._vispy.overlays.crosshair import VispyCrosshairVisual
from qtextra._napari.common.components.overlays.color_bar import ColorBarOverlay
from qtextra._napari.common.components.overlays.crosshair import CrossHairOverlay

overlay_to_visual.update(
    {
        CrossHairOverlay: VispyCrosshairVisual,
        ColorBarOverlay: VispyColorbarOverlay,
    }
)

__all__ = ["create_vispy_overlay", "overlay_to_visual"]
