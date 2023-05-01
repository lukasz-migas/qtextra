from napari.layers.points._points_constants import Mode
from napari.layers.points.points import Points


@Points.bind_key("Space", overwrite=True)
def hold_to_pan_zoom(layer):
    """Hold to pan and zoom in the viewer."""
    if layer._mode != Mode.PAN_ZOOM:
        # on key press
        prev_mode = layer.mode
        prev_selected = layer.selected_data.copy()
        layer.mode = Mode.PAN_ZOOM

        yield

        # on key release
        layer.mode = prev_mode
        layer.selected_data = prev_selected
        layer._set_highlight()


@Points.bind_key("P", overwrite=True)
def activate_add_mode(layer):
    """Activate add points tool."""
    layer.mode = Mode.ADD


@Points.bind_key("S", overwrite=True)
def activate_select_mode(layer):
    """Activate select points tool."""
    layer.mode = Mode.SELECT


@Points.bind_key("Z", overwrite=True)
def activate_pan_zoom_mode(layer):
    """Activate pan and zoom mode."""
    layer.mode = Mode.PAN_ZOOM


@Points.bind_key("Control-C", overwrite=True)
def copy(layer):
    """Copy any selected points."""
    if layer._mode == Mode.SELECT:
        layer._copy_data()


@Points.bind_key("Control-V", overwrite=True)
def paste(layer):
    """Paste any copied points."""
    if layer._mode == Mode.SELECT:
        layer._paste_data()


@Points.bind_key("A", overwrite=True)
def select_all(layer):
    """Select all points in the current view slice."""
    if layer._mode == Mode.SELECT:
        layer.selected_data = set(layer._indices_view[: len(layer._view_data)])
        layer._set_highlight()


@Points.bind_key("Backspace", overwrite=True)
@Points.bind_key("Delete", overwrite=True)
def delete_selected(layer):
    """Delete all selected points."""
    if layer._mode in (Mode.SELECT, Mode.ADD):
        layer.remove_selected()
