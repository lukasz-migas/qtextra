"""Layer utilities."""
from napari._vispy.layers.base import VispyBaseLayer
from napari._vispy.layers.image import VispyImageLayer
from napari._vispy.layers.labels import VispyLabelsLayer
from napari._vispy.layers.points import VispyPointsLayer
from napari._vispy.layers.shapes import VispyShapesLayer
from napari.layers import Image, Labels, Layer, Points, Shapes

# from qtextra._napari.image.layers import Labels, Layer, Points, Shapes

layer_to_visual = {
    Image: VispyImageLayer,
    Labels: VispyLabelsLayer,
    Shapes: VispyShapesLayer,
    Points: VispyPointsLayer,
}


def create_vispy_visual(layer: Layer) -> VispyBaseLayer:
    """Create vispy visual for a layer based on its layer type.

    Parameters
    ----------
    layer : napari.layers._base_layer.Layer
        Layer that needs its property widget created.

    Returns
    -------
    visual : vispy.scene.visuals.VisualNode
        Vispy visual node
    """
    for layer_type, visual_class in layer_to_visual.items():
        if isinstance(layer, layer_type):
            return visual_class(layer)

    raise TypeError(f"Could not find VispyLayer for layer of type {type(layer)}")
