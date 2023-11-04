"""Init."""
try:
    import napari
except ImportError:
    raise ImportError("please install napari using 'pip install napari'") from None

try:
    import napari_plot
except ImportError:
    pass
    # raise ImportError("please install napari using 'pip install napari-plot'") from None


# Monkey patch icons
import napari.resources._icons

from qtextra.assets import ICONS

# overwrite napari list of icons
# This is required because we've added several new layer types that have custom icons associated with them.
napari.resources._icons.ICONS = ICONS
