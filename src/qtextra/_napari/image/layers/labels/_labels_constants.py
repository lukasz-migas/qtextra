import sys
from collections import OrderedDict

from napari.layers.labels._labels_constants import LabelColorMode

BACKSPACE = "delete" if sys.platform == "darwin" else "backspace"

LABEL_COLOR_MODE_TRANSLATIONS = OrderedDict(
    [
        (LabelColorMode.AUTO, "auto"),
        (LabelColorMode.DIRECT, "direct"),
    ]
)
