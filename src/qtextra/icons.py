"""Base icon functions."""

import re
import typing as ty
from functools import lru_cache
from itertools import product
from pathlib import Path


def get_icon_path(name: str) -> str:
    """Return path to an SVG in the theme icons."""
    from qtextra.assets import ICONS

    if name not in ICONS:
        raise ValueError(f"unrecognized icon name: {name!r}. Known names: {ICONS}")
    return ICONS[name]


svg_elem = re.compile(r"(<svg[^>]*>)")
svg_style = """<style type="text/css">
path {{fill: {0}; opacity: {1};}}
polygon {{fill: {0}; opacity: {1};}}
circle {{fill: {0}; opacity: {1};}}
rect {{fill: {0}; opacity: {1};}}
</style>"""


@lru_cache
def get_raw_svg(path: str) -> str:
    """Get and cache SVG XML."""
    return Path(path).read_text()


@lru_cache
def get_colorized_svg(path_or_xml: ty.Union[str, Path], color: ty.Optional[str] = None, opacity=1) -> str:
    """Return a colorized version of the SVG XML at ``path``.

    Raises
    ------
    ValueError
        If the path exists but does not contain valid SVG data.
    """
    path_or_xml = str(path_or_xml)
    xml = path_or_xml if "</svg>" in path_or_xml else get_raw_svg(path_or_xml)
    if not color:
        return xml

    if not svg_elem.search(xml):
        raise ValueError(f"Could not detect svg tag in {path_or_xml!r}")
    # use regex to find the svg tag and insert css right after
    # (the '\\1' syntax includes the matched tag in the output)
    return svg_elem.sub(f"\\1{svg_style.format(color, opacity)}", xml)


def generate_colorized_svgs(
    svg_paths: ty.Iterable[ty.Union[str, Path]],
    colors: ty.Iterable[ty.Union[str, ty.Tuple[str, str]]],
    opacities: ty.Iterable[float] = (1.0,),
    theme_override: ty.Optional[ty.Dict[str, str]] = None,
) -> ty.Iterator[ty.Tuple[str, str]]:
    """Helper function to generate colorized SVGs.

    This is a generator that yields tuples of ``(alias, icon_xml)`` for every
    combination (Cartesian product) of `svg_path`, `color`, and `opacity`
    provided. It can be used as input to :func:`_temporary_qrc_file`.

    Parameters
    ----------
    svg_paths : Iterable[Union[str, Path]]
        An iterable of paths to svg files
    colors : Iterable[Union[str, Tuple[str, str]]]
        An iterable of colors.  Every icon will be generated in every color. If
        a `color` item is a string, it should be valid svg color style. Items
        may also be a 2-tuple of strings, in which case the first item should
        be an available theme name
        (:func:`~napari.utils.theme.available_themes`), and the second item
        should be a key in the theme (:func:`~napari.utils.theme.get_theme`),
    opacities : Iterable[float], optional
        An iterable of opacities to generate, by default (1.0,) Opacities less
        than one can be accessed in qss with the opacity as a percentage
        suffix, e.g.: ``my_svg_50.svg`` for opacity 0.5.
    theme_override : Optional[Dict[str, str]], optional
        When one of the `colors` is a theme ``(name, key)`` tuple,
        `theme_override` may be used to override the `key` for a specific icon
        name in `svg_paths`.  For example ``{'exclamation': 'warning'}``, would
        use the theme "warning" color for any icon named "exclamation.svg" by
        default `None`

    Yields
    ------
    (alias, xml) : Iterator[Tuple[str, str]]
        `alias` is the name that will used to access the icon in the Qt
        Resource system (such as QSS), and `xml` is the *raw* colorzied SVG
        text (as read from a file, perhaps pre-colored using one of the below
        functions).
    """
    from qtextra.config.theme import THEMES

    # mapping of svg_stem to theme_key
    theme_override = theme_override or {}

    ALIAS_T = "{color}/{svg_stem}{opacity}.svg"

    for color, path, op in product(colors, svg_paths, opacities):
        clrkey = color
        svg_stem = Path(path).stem
        if isinstance(color, tuple):
            clrkey, theme_key = color
            theme_key = theme_override.get(svg_stem, theme_key)
            color = getattr(THEMES[clrkey], theme_key).as_hex()
            # convert color to string to fit get_colorized_svg signature

        op_key = "" if op == 1 else f"_{op * 100:.0f}"
        alias = ALIAS_T.format(color=clrkey, svg_stem=svg_stem, opacity=op_key)
        yield alias, get_colorized_svg(path, color, op)


def write_colorized_svgs(
    dest: ty.Union[str, Path],
    svg_paths: ty.Iterable[ty.Union[str, Path]],
    colors: ty.Iterable[ty.Union[str, ty.Tuple[str, str]]],
    opacities: ty.Iterable[float] = (1.0,),
    theme_override: ty.Optional[ty.Dict[str, str]] = None,
) -> None:
    """Write colorized SVGs to a directory."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    svgs = generate_colorized_svgs(
        svg_paths=svg_paths,
        colors=colors,
        opacities=opacities,
        theme_override=theme_override,
    )

    for alias, svg in svgs:
        (dest / Path(alias).name).write_text(svg)


def build_theme_svgs(theme_name: str) -> str:
    """Build SVGs for a theme."""
    from qtextra.assets import ICONS
    from qtextra.config.theme import THEMES

    out = THEMES.get_theme_path(theme_name)
    write_colorized_svgs(
        out,
        svg_paths=ICONS.values(),
        colors=[(theme_name, "icon")],
        opacities=(0.5, 1),
        theme_override={
            "warning": "warning",
            "error": "error",
            "logo_silhouette": "background",
        },
    )
    with (out / "plugin.txt").open("w") as f:
        f.write("builtin")
    return str(out)
