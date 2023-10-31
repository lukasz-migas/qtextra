# syntax_style for the console must be one of the supported styles from
# pygments - see here for examples https://help.farbox.com/pygments.html
import re
import typing as ty
from ast import literal_eval

from pydantic.color import Color

from qtextra.utils.color import get_text_color, hex_to_qt_rgb, rgb_to_hex

try:
    from qtpy import QT_VERSION

    major, minor, *rest = QT_VERSION.split(".")
    use_gradients = (int(major) >= 5) and (int(minor) >= 12)
except Exception:
    use_gradients = False


increase_pattern = re.compile(r"{{\s?increase\((\w+),?\s?([-\d]+)?\)\s?}}")
decrease_pattern = re.compile(r"{{\s?decrease\((\w+),?\s?([-\d]+)?\)\s?}}")
gradient_pattern = re.compile(r"([vh])gradient\((.+)\)")
darken_pattern = re.compile(r"{{\s?darken\((\w+),?\s?([-\d]+)?\)\s?}}")
lighten_pattern = re.compile(r"{{\s?lighten\((\w+),?\s?([-\d]+)?\)\s?}}")
opacity_pattern = re.compile(r"{{\s?opacity\((\w+),?\s?([-\d]+)?\)\s?}}")
replace_pattern = re.compile(r"{{\s?replace\((\w+)\)\s?}}")


def decrease(font_size: str, pt: int) -> str:
    """Decrease fontsize."""
    return f"{int(font_size[:-2]) - int(pt)}pt"


def increase(font_size: str, pt: int) -> str:
    """Increase fontsize."""
    return f"{int(font_size[:-2]) + int(pt)}pt"


def color_for_background(color: ty.Union[str, Color]) -> str:
    """Return color that will stand out against background color."""
    if isinstance(color, str):
        if color.startswith("#"):
            color = hex_to_qt_rgb(color)
        if color.startswith("rgb("):
            color = literal_eval(color.lstrip("rgb(").rstrip(")"))
    else:
        color = color.as_rgb_tuple()
    return get_text_color(rgb_to_hex(color, 1)).name()


def darken(color: ty.Union[str, Color], percentage=10) -> str:
    """Darken the color."""
    if isinstance(color, str):
        if color.startswith("#"):
            color = hex_to_qt_rgb(color)
        if color.startswith("rgb("):
            color = literal_eval(color.lstrip("rgb(").rstrip(")"))
    else:
        color = color.as_rgb_tuple()
    ratio = 1 - float(percentage) / 100
    red, green, blue = color
    red = min(max(int(red * ratio), 0), 255)
    green = min(max(int(green * ratio), 0), 255)
    blue = min(max(int(blue * ratio), 0), 255)
    return f"rgb({red}, {green}, {blue})"


def lighten(color: ty.Union[str, Color], percentage=10) -> str:
    """Lighten the color."""
    if isinstance(color, str):
        if color.startswith("#"):
            color = hex_to_qt_rgb(color)
        if color.startswith("rgb("):
            color = literal_eval(color.lstrip("rgb(").rstrip(")"))
    else:
        color = color.as_rgb_tuple()
    ratio = float(percentage) / 100
    red, green, blue = color
    red = min(max(int(red + (255 - red) * ratio), 0), 255)
    green = min(max(int(green + (255 - green) * ratio), 0), 255)
    blue = min(max(int(blue + (255 - blue) * ratio), 0), 255)
    return f"rgb({red}, {green}, {blue})"


def opacity(color: ty.Union[str, Color], value=255) -> str:
    """Adjust opacity."""
    if isinstance(color, str):
        if color.startswith("#"):
            color = hex_to_qt_rgb(color)
        if color.startswith("rgb("):
            color = literal_eval(color.lstrip("rgb(").rstrip(")"))
    else:
        color = color.as_rgb_tuple()
    red, green, blue = color
    return f"rgba({red}, {green}, {blue}, {max(min(int(value), 255), 0)})"


def gradient(stops, horizontal=True) -> str:
    """Make gradient."""
    if not use_gradients:
        return stops[-1]

    if horizontal:
        grad = "qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, "
    else:
        grad = "qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, "

    _stops = [f"stop: {n} {stop}" for n, stop in enumerate(stops)]
    grad += ", ".join(_stops) + ")"
    return grad


def template(css, **theme):
    """Generate template."""

    def _increase_match(matchobj):
        font_size, to_add = matchobj.groups()
        return increase(theme[font_size], to_add)

    def _decrease_match(matchobj):
        font_size, to_subtract = matchobj.groups()
        return decrease(theme[font_size], to_subtract)

    def _darken_match(matchobj):
        color, percentage = matchobj.groups()
        return darken(theme[color], percentage)

    def _lighten_match(matchobj):
        color, percentage = matchobj.groups()
        return lighten(theme[color], percentage)

    def _opacity_match(matchobj):
        color, percentage = matchobj.groups()
        return opacity(theme[color], percentage)

    def _replace_match(matchobj):
        color = matchobj.groups()[0]
        return color_for_background(theme[color])

    def _gradient_match(matchobj):
        horizontal = matchobj.groups()[1] == "h"
        stops = [i.strip() for i in matchobj.groups()[1].split("-")]
        return gradient(stops, horizontal)

    for k, v in theme.items():
        if k == "name":
            k = "id"
        css = increase_pattern.sub(_increase_match, css)
        css = decrease_pattern.sub(_decrease_match, css)
        css = gradient_pattern.sub(_gradient_match, css)
        css = darken_pattern.sub(_darken_match, css)
        css = lighten_pattern.sub(_lighten_match, css)
        css = opacity_pattern.sub(_opacity_match, css)
        css = replace_pattern.sub(_replace_match, css)
        if isinstance(v, Color):
            v = v.as_rgb()
        css = css.replace("{{ %s }}" % k, v)
    return css
