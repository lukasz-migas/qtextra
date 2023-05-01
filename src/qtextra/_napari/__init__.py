"""Init."""
# Monkey patch icons
import napari.resources._icons

from qtextra.icons import ICONS

# overwrite napari list of icons
# This is required because we've added several new layer types that have custom icons associated with them.
napari.resources._icons.ICONS = ICONS
