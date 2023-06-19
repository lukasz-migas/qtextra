import numpy as np


def convert_histogram_to_shapes(bin_edges: np.ndarray, bin_values: np.ndarray, orientation: str = "vertical"):
    """Convert x/y-axis values into shapes.

    To create a histogram:
    1. Determine histogram centers
    2. Determine width
    3. Create boxes
    """
    shapes = []
    for i in range(10):
        shapes.append((((0, i - 0.5), (0, i + 0.5), (i, i + 0.5), (i, i - 0.5)), "rectangle"))
    return shapes


def convert_hist_to_shapes(array: np.ndarray, bins: int, orientation: str = "vertical", rel_width: float = 0.8):
    """Convert histogram to shape."""
    tops, lefts = np.histogram(array, bins=bins)
    bottoms = np.zeros_like(tops)
    width = np.diff(lefts)
    centers = lefts[:-1] + width
    width = (rel_width * width.mean()) / 2
    lefts = centers - width
    rights = centers + width
    # rights = lefts + width
    shapes = []
    for left, right, bottom, top in zip(lefts, rights, bottoms, tops):
        if orientation == "horizontal":
            shapes.append((((left, bottom), (right, bottom), (right, top), (left, top)), "rectangle"))
        else:
            shapes.append((((bottom, left), (bottom, right), (top, right), (top, left)), "rectangle"))
    return shapes


def update_attributes(layer, throw_exception: bool = True, **kwargs):
    """Update attributes on the layer."""
    for attr, value in kwargs.items():
        try:
            setattr(layer, attr, value)
        except (AttributeError, ValueError) as err:
            if throw_exception:
                raise err
