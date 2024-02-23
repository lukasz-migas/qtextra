"""Assets."""
import typing as ty
from pathlib import Path

from loguru import logger

from qtextra.utils.utilities import get_module_path

HERE = Path(get_module_path("qtextra.assets", "__init__.py")).parent.resolve()

ICON_PATH = HERE / "icons"
ICON_PATH.mkdir(exist_ok=True)
ICONS = {x.stem: str(x) for x in ICON_PATH.iterdir() if x.suffix == ".svg"}

STYLE_PATH = HERE / "stylesheets"
STYLE_PATH.mkdir(exist_ok=True)
STYLES = {x.stem: str(x) for x in STYLE_PATH.iterdir() if x.suffix == ".qss"}

LOADING_SQUARE_GIF = str(HERE / "loading-square.gif")
LOADING_CIRCLE_GIF = str(HERE / "loading-circle.gif")

QTA_MAPPING: ty.Dict[str, str] = {
    "MISSING": "ri.error-warning-line",
    "open": "fa5s.folder-open",
    "folder": "mdi.folder-move-outline",
    "cross": "fa5s.times",
    "cross_full": "fa5s.times-circle",
    "minimise": "fa5s.window-minimize",
    "help": "mdi.help-circle-outline",
    "clipboard": "fa5s.clipboard-list",
    "colorbar": "mdi.invert-colors",
    "chevron_down_circle": "fa5s.chevron-circle-down",
    "chevron_up_circle": "fa5s.chevron-circle-up",
    "chevron_left_circle": "fa5s.chevron-circle-left",
    "chevron_right_circle": "fa5s.chevron-circle-right",
    "save": "ri.save-2-fill",
    "gear": "ph.gear-fill",
    "zoom_out": "fa5s.expand",
    "ruler": "ph.ruler",
    "text": "mdi.format-text",
    "crosshair": "ph.crosshair-simple",
    "grid": "mdi.grid",
    "layers": "fa5s.layer-group",
    "rectangle": "ph.rectangle-bold",
    "ellipse": "mdi6.ellipse-outline",
    "polygon": "mdi.pentagon-outline",
    "none": "mdi6.cancel",
    "move": "ei.move",
    "move_handle": "ei.move",
    "lasso": "mdi6.lasso",
    "marker": "fa5s.map-marker-alt",
    "zoom": "mdi.magnify",
    "new_labels": "fa5s.tag",
    "erase": "ph.eraser-fill",
    "new": "mdi.new-box",
    "check": "fa5s.check",
    "edit": "ri.edit-box-fill",
    "remove": "ri.indeterminate-circle-line",
    "light_theme": "ri.sun-fill",
    "dark_theme": "ri.moon-clear-fill",
    "delete": "fa5s.trash-alt",
    "new_points": "mdi.scatter-plot",
    "new_shapes": "fa5s.shapes",
    "ndisplay_off": "ph.square",
    "ndisplay_on": "ph.cube",
    "roll": "mdi6.rotate-right-variant",
    "transpose": "ri.t-box-line",
    "grid_off": "mdi6.grid-off",
    "grid_on": "mdi6.grid",
    "home": "fa5s.home",
    "pan_zoom": "ei.move",
    "select": "fa5s.location-arrow",
    "add_points": "ri.add-circle-fill",
    "select_points": "fa5s.location-arrow",
    "delete_shape": "fa5s.times",
    "move_back": "mdi6.arrange-send-backward",
    "move_front": "mdi6.arrange-bring-to-front",
    "line": "mdi6.line",
    "path": "mdi.chart-line-variant",
    "vertex_insert": "mdi.map-marker-plus",
    "vertex_remove": "mdi.map-marker-minus",
    "vertex_select": "mdi.map-marker-check",
    "shuffle": "ph.shuffle-bold",
    "picker": "mdi6.eyedropper",
    "paint": "fa5s.paint-brush",
    "fill": "fa5s.fill-drip",
    "cancel": "mdi.close-circle",
    "success": "mdi.check-circle",
    "paint_palette": "ph.palette-fill",
    "warning": "fa.warning",
}


def update_icon_mapping(mapping: ty.Dict[str, str]) -> None:
    """Update icon mapping."""
    global QTA_MAPPING
    QTA_MAPPING.update(mapping)


def update_styles(mapping: ty.Dict[str, str]) -> None:
    """Update icon mapping."""
    global STYLES
    STYLES.update(mapping)


def update_icons(mapping: ty.Dict[str, str]) -> None:
    """Update icon mapping."""
    global ICONS
    ICONS.update(mapping)


def get_icon(name: str):
    """Return icon."""
    original_name = name
    if name == "":
        return name
    if "." not in name:
        name = QTA_MAPPING.get(name)
        if name is None:
            logger.warning(f"Failed to retrieve icon: '{original_name}'")
            name = QTA_MAPPING["MISSING"]
    return name


def get_stylesheet(theme: ty.Optional[str] = None, extra: ty.Optional[ty.List[str]] = None) -> str:
    """Combine all qss files into single, possibly pre-themed, style string.

    Parameters
    ----------
    theme : str, optional
        Theme to apply to the stylesheet. If no theme is provided, the returned
        stylesheet will still have ``{{ template_variables }}`` that need to be
        replaced using the :func:`qtextra.template` function prior
        to using the stylesheet.
    extra : list of str, optional
        Additional paths to QSS files to include in stylesheet, by default None

    Returns
    -------
    css : str
        The combined stylesheet.
    """
    stylesheet = ""
    for key in sorted(STYLES):
        file = STYLES[key]
        with open(file) as f:
            stylesheet += f.read()
    if extra:
        for file in extra:
            with open(file) as f:
                stylesheet += f.read()

    if theme:
        from qtextra.config.theme import THEMES
        from qtextra.utils.template import template

        return template(stylesheet, **THEMES.get_theme(theme, as_dict=True))

    return stylesheet
