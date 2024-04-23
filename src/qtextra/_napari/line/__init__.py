"""Init."""

# Need to import to ensure that `qtextra` to modify mouse action
from qtextra._napari.line.components import _viewer_mouse_bindings

from .wrapper import NapariLineView

__all__ = ["NapariLineView"]
