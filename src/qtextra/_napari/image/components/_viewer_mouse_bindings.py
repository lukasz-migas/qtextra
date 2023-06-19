"""Mouse bindings to the viewer."""


def crosshair(viewer, event):
    """Enable crosshair."""
    if "Control" not in event.modifiers:
        return

    if not viewer.cross_hair.visible:
        viewer.cross_hair.visible = True

    # on mouse press
    if event.type == "mouse_press":
        viewer.cross_hair.position = event.position
        viewer.events.crosshair(position=event.position)
        yield

    # on mouse move
    while event.type == "mouse_move" and "Control" in event.modifiers:
        viewer.cross_hair.position = event.position
        viewer.events.crosshair(position=event.position)
        yield

    # on mouse release
    if viewer.cross_hair.auto_hide:
        viewer.cross_hair.visible = False
    yield
