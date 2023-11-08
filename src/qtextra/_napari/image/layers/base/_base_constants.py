"""Base constants."""
from collections import OrderedDict

from napari.layers.base._base_constants import Blending

BLENDING_TRANSLATIONS = OrderedDict(
    [
        (Blending.TRANSLUCENT, "Translucent"),
        (Blending.TRANSLUCENT_NO_DEPTH, "Translucent (no depth)"),
        (Blending.ADDITIVE, "Additive"),
        (Blending.OPAQUE, "Opaque"),
        (Blending.MINIMUM, "Minimum"),
    ]
)
