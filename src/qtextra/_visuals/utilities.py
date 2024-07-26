"""Utilities."""

import numpy as np
from matplotlib.ticker import FuncFormatter

__all__ = ("compute_divider", "y_tick_fmt", "get_intensity_formatter", "make_listed_colormap", "make_centroid_lines")


def compute_divider(value):
    """Compute divider."""
    divider = 1000000000
    value = abs(value)
    while value == value % divider:
        divider /= 1000
    return len(str(int(divider))) - len(str(int(divider)).rstrip("0"))


def find_text_color(base_color, dark_color="black", light_color="white", coef_choice=0):
    """
    Takes a background color and returns the appropriate light or dark text color.
    Users can specify the dark and light text color, or accept the defaults of 'black' and 'white'
    base_color: The color of the background. This must be
        specified in RGBA with values between 0 and 1 (note, this is the default
        return value format of a call to base_color = cmap(number) to get the
        color corresponding to a desired number). Note, the value of `A` in RGBA
        is not considered in determining light/dark.
    dark_color: Any valid matplotlib color value.
        Function will return this value if the text should be colored dark
    light_color: Any valid matplotlib color value.
        Function will return this value if thet text should be colored light.
    coef_choice: slightly different approaches to calculating brightness. Currently two options in
        a list, user can enter 0 or 1 as list index. 0 is default.
    """
    # Coefficients:
    # option 0: http://www.nbdtech.com/Blog/archive/2008/04/27/Calculating-the-Perceived-Brightness-of-a-Color.aspx
    # option 1: http://stackoverflow.com/questions/596216/formula-to-determine-brightness-of-rgb-color
    coef_options = [
        np.array((0.241, 0.691, 0.068, 0)),
        np.array((0.299, 0.587, 0.114, 0)),
    ]

    coefs = coef_options[coef_choice]
    rgb = np.array(base_color) * 255
    brightness = np.sqrt(np.dot(coefs, rgb**2))

    # Threshold from option 0 link; determined by trial and error.
    # base is light
    if brightness > 130:
        return dark_color
    return light_color


def y_tick_fmt(x, pos):
    """Y-tick formatter."""

    def _convert_divider_to_str(value, exp_value):
        value = float(value)
        if exp_value in [0, 1, 2]:
            if abs(value) <= 1:
                return f"{value:.2G}"
            elif abs(value) <= 1000:
                if value.is_integer():
                    return f"{value:.0F}"
                return f"{value:.1F}"
        elif exp_value in [3, 4, 5]:
            return f"{value / 1000:.1f}k"
        elif exp_value in [6, 7, 8]:
            return f"{value / 1000000:.1f}M"
        elif exp_value in [9, 10, 11, 12]:
            return f"{value / 1000000000:.1f}B"

    return _convert_divider_to_str(x, compute_divider(x))


def get_intensity_formatter():
    """Simple intensity formatter."""
    return FuncFormatter(y_tick_fmt)


def make_listed_colormap(colors: list[str], is_vispy: bool = False):
    """Make listed colormap."""
    from matplotlib.colors import LinearSegmentedColormap
    from vispy.color.colormap import Colormap

    if is_vispy:
        colors.insert(0, "#FFFFFF")

    colormap = LinearSegmentedColormap.from_list("colormap", colors, len(colors))
    if is_vispy:
        mpl_colors = colormap(np.linspace(0, 1, len(colors)))
        mpl_colors[0][-1] = 0  # first color is white with alpha=0
        return Colormap(mpl_colors)
    return colormap


def make_centroid_lines(x: np.ndarray, y: np.ndarray):
    """Make centroids."""
    lines = []
    for i in range(len(x)):
        pair = [(x[i], 0), (x[i], y[i])]
        lines.append(pair)
    return lines
