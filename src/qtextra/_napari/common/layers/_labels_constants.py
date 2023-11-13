from collections import OrderedDict

from napari.layers.labels._labels_constants import LabelColorMode, LabelsRendering

RENDER_MODE_TRANSLATIONS = OrderedDict(
    [
        (LabelsRendering.TRANSLUCENT, "Translucent"),
        (LabelsRendering.ISO_CATEGORICAL, "Iso-categorical"),
    ]
)

LABEL_COLOR_MODE_TRANSLATIONS = OrderedDict(
    [
        (LabelColorMode.AUTO, "auto"),
        (LabelColorMode.DIRECT, "direct"),
    ]
)
