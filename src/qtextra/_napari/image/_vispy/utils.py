"""Layer utilities."""
from napari._vispy.layers.image import VispyImageLayer
from napari._vispy.layers.labels import VispyLabelsLayer
from napari._vispy.layers.points import VispyPointsLayer
from napari._vispy.layers.shapes import VispyShapesLayer
from napari.layers import Image, Labels, Points, Shapes

# from qtextra._napari.image.layers import Labels, Layer, Points, Shapes

layer_to_visual = {
    Image: VispyImageLayer,
    Labels: VispyLabelsLayer,
    Shapes: VispyShapesLayer,
    Points: VispyPointsLayer,
}
