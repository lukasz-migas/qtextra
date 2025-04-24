"""Assets."""

from __future__ import annotations

import typing as ty
from pathlib import Path

from koyo.utilities import get_module_path
from loguru import logger

HERE = Path(get_module_path("qtextra.assets", "__init__.py")).parent.resolve()

ICON_PATH = HERE / "icons"
ICON_PATH.mkdir(exist_ok=True)
ICONS = {x.stem: str(x) for x in ICON_PATH.iterdir() if x.suffix == ".svg"}

STYLE_PATH = HERE / "stylesheets"
STYLE_PATH.mkdir(exist_ok=True)
STYLES = {x.stem: str(x) for x in STYLE_PATH.iterdir() if x.suffix == ".qss"}

# Some gifs were made using https://loading.io/
# orange color = #ff4500
LOADING_SQUARE_GIF = str(HERE / "gifs" / "loading-square.gif")
LOADING_CIRCLE_GIF = str(HERE / "gifs" / "loading-circle.gif")
LOADING_DOTS_GIF = str(HERE / "gifs" / "loading-dots.gif")
LOADING_INFINITY_GIF = str(HERE / "gifs" / "loading-infinity.gif")
LOADING_OVAL_GIF = str(HERE / "gifs" / "loading-oval.gif")

LOADING_GIFS = {
    "square": LOADING_SQUARE_GIF,
    "circle": LOADING_CIRCLE_GIF,
    "dots": LOADING_DOTS_GIF,
    "infinity": LOADING_INFINITY_GIF,
    "oval": LOADING_OVAL_GIF,
}

MISSING = "MISSING"

QTA_MAPPING: ty.Dict[str, str | tuple[str, dict]] = {
    MISSING: "ri.error-warning-line",
    "clear": "mdi6.delete-empty",
    "json": "mdi6.code-json",
    "binary": "msc.file-binary",
    "hdf5": "fa5s.file",
    "open": "fa5s.folder-open",
    "folder": "mdi.folder-move-outline",
    "cross": "fa5s.times",
    "cross_full": "fa5s.times-circle",
    "minimise": "fa5s.window-minimize",
    "help": "mdi.help-circle-outline",
    "clipboard": "fa5s.clipboard-list",
    "colorbar": "mdi.invert-colors",
    "gear": "ph.gear-fill",
    "zoom_out": "fa5s.expand",
    "ruler": "ph.ruler",
    "ipython": "mdi.console",
    "cli": "mdi6.console-line",
    "template": "ei.file-new",
    # "log": "mdi6.file-document",
    "log": "mdi6.clipboard-text",
    "filter_and": "mdi6.filter-plus",
    "filter_or": "mdi6.filter-minus",
    "and": "mdi6.ampersand",
    "or": "fa5s.grip-lines-vertical",
    # "ruler": "fa5s.ruler-horizontal",
    "text": "mdi.format-text",
    "crosshair": "ph.crosshair-simple",
    "none": "mdi6.cancel",
    "move": "ei.move",
    "move_handle": "ei.move",
    "lasso": "mdi6.lasso",
    "marker": "fa5s.map-marker-alt",
    "zoom": "mdi.magnify",
    "erase": "ph.eraser-fill",
    "new": "mdi.new-box",
    # "check": "fa5s.check",
    "edit": "ri.edit-box-fill",
    "add": "ri.add-circle-line",
    "remove": "ri.indeterminate-circle-line",
    "check": "ri.checkbox-circle-line",
    "delete": "fa5s.trash-alt",
    "shuffle": "ph.shuffle-bold",
    "picker": "mdi6.eyedropper",
    "paint": "fa5s.paint-brush",
    "fill": "fa5s.fill-drip",
    "cancel": "mdi.close-circle",
    "paint_palette": "ph.palette-fill",
    "copy_to_clipboard": "mdi.clipboard-arrow-left-outline",
    "copy": "fa6.copy",
    "copy_all": "fa6s.copy",
    "sort": "fa5s.sort-amount-up",
    "sort_ascending": "fa5s.sort-amount-up",
    "sort_descending": "fa5s.sort-amount-down",
    "graph": "mdi.graph",
    "reload": "mdi6.cached",
    "replace": "msc.replace",
    "save": "fa5s.save",
    "screenshot": "mdi.camera-outline",
    "github": "fa5b.github",
    "request": "msc.request-changes",
    "web": "mdi.web",
    "bug": "fa5s.bug",
    "info": "fa5s.info-circle",
    "warning": "fa5s.exclamation-triangle",
    "error": "fa5s.times-circle",
    "critical": "fa5s.times-circle",
    "debug": "ph.megaphone",
    "success": "fa5s.check",
    "true": "mdi6.check-circle-outline",
    "false": "mdi6.close-circle-outline",
    "axes_label": "mdi.axis-arrow",
    "close": "fa5s.trash-alt",
    "list": "mdi6.format-list-bulleted",
    "pin": "fa5s.map-pin",
    "repeat": "fa5s.redo",
    "more": "mdi.dots-horizontal-circle",
    "previous": "fa5s.chevron-circle-left",
    "next": "fa5s.chevron-circle-right",
    "star": "fa5s.star",
    "cpu": "ri.cpu-line",
    "ram": "fa5s.memory",
    "upgrade": "ei.download",
    "schema": "mdi6.badge-account-horizontal",
    "locked": "mdi.lock",
    "unlocked": "mdi.lock-open",
    "notified": "mdi6.bell",
    "not_notified": "mdi6.bell-off",
    # notification
    "notification": "mdi6.bell",
    "notification_on": "mdi6.bell",
    "notification_off": "mdi6.bell-badge",
    "notification_dismiss": "mdi6.bell-cancel",
    "notification_check": "mdi6.bell-check",
    # translate
    "rotate_left": "fa6s.rotate-left",
    "rotate_right": "fa6s.rotate-right",
    "translate_left": "fa5s.arrow-left",
    "translate_right": "fa5s.arrow-right",
    "translate_up": "fa5s.arrow-up",
    "translate_down": "fa5s.arrow-down",
    "flip_lr": "fa5s.arrows-alt-h",
    "flip_ud": "fa5s.arrows-alt-v",
    "group": "mdi6.group",
    "ungroup": "mdi6.ungroup",
    # app
    "settings": "mdi6.tools",
    "reset": "mdi.lock-reset",
    # "update": "ei.refresh",
    "update": "fa5s.redo-alt",
    "version": "mdi6.update",
    "telemetry": "mdi.telegram",
    "shortcut": "mdi6.tooltip-text",
    "feedback": "msc.feedback",
    "handshake": "fa5.handshake",
    "dev": "mdi6.code-braces",
    # arrows
    "arrow_up": "fa5s.arrow-up",
    "arrow_down": "fa5s.arrow-down",
    "arrow_left": "fa5s.arrow-left",
    "arrow_right": "fa5s.arrow-right",
    "long_arrow_up": "fa5s.long-arrow-alt-up",
    "long_arrow_down": "fa5s.long-arrow-alt-down",
    "long_arrow_left": "fa5s.long-arrow-alt-left",
    "long_arrow_right": "fa5s.long-arrow-alt-right",
    "caret_left": "fa5s.caret-left",
    "caret_right": "fa5s.caret-right",
    "caret_up": "fa5s.caret-up",
    "caret_down": "fa5s.caret-down",
    # run/play
    "run": "mdi6.run-fast",
    "start": "fa5s.play-circle",
    "retry": "fa5s.redo-alt",
    "stop": "fa5s.stop-circle",
    "pause": "fa5s.pause-circle",
    # "queue": "ph.queue-fill",
    "queue": "mdi6.human-queue",
    # lock
    "lock_closed": "fa5s.lock",
    "lock_open": "fa5s.lock-open",
    # theme
    "light_theme": "ri.sun-fill",
    "dark_theme": "ri.moon-clear-fill",
    # chevrons
    "chevron_down": "fa5s.chevron-down",
    "chevron_up": "fa5s.chevron-up",
    "chevron_left": "fa5s.chevron-left",
    "chevron_right": "fa5s.chevron-right",
    "chevron_down_circle": "fa5s.chevron-circle-down",
    "chevron_up_circle": "fa5s.chevron-circle-up",
    "chevron_left_circle": "fa5s.chevron-circle-left",
    "chevron_right_circle": "fa5s.chevron-circle-right",
    # toggles
    "toggle_on": "mdi.checkbox-marked",
    "toggle_off": "mdi.checkbox-blank-outline",
    # visible
    "visible": "ei.eye-open",
    "visible_on": "ei.eye-open",
    "visible_off": "ei.eye-close",
    # priority
    "priority_high": "mdi6.chevron-triple-up",
    "priority_normal": "ph.equals-fill",
    "priority_low": "mdi6.chevron-triple-down",
    # viewer
    "new_line": "msc.pulse",
    "new_surface": "ei.star",
    "new_labels": "fa5s.tag",
    "new_points": "mdi.scatter-plot",
    "new_shapes": "fa5s.shapes",
    "new_inf_line": "mdi.infinity",
    "new_centroids": "ri.bar-chart-fill",
    "new_region": "ri.bar-chart-horizontal-fill",
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
    "line": "ph.line-segment-fill",
    "path": "mdi.chart-line-variant",
    "vertex_insert": "mdi.map-marker-plus",
    "vertex_remove": "mdi.map-marker-minus",
    "vertex_select": "mdi.map-marker-check",
    "grid": "mdi.grid",
    "layers": "fa5s.layer-group",
    "rectangle": "ph.rectangle-bold",
    "ellipse": "mdi6.ellipse-outline",
    "polygon": "mdi.pentagon-outline",
    # selection
    "invert_selection": "fa5s.exchange-alt",
    "pin_on": ("ph.push-pin-fill", {"rotated": -45}),
    "pin_off": "ph.push-pin-fill",
    "minimize": "fa5s.window-minimize",
    "maximize": "fa5s.window-maximize",
    "fullscreen": "fa5s.expand",
    "random": "fa5s.random",
    "color_palette": "fa5s.palette",
    "magic": "mdi6.auto-fix",
    "approve": "fa5s.thumbs-up",
    "reject": "fa5s.thumbs-down",
    "target": "mdi.target",
}


def update_icon_mapping(mapping: ty.Dict[str, str]) -> None:
    """Update icon mapping."""
    global QTA_MAPPING
    for k, v_new in mapping.items():
        v_exist = QTA_MAPPING.get(k, None)
        v_new = mapping[k]
        if v_exist and v_exist == v_new:
            print(f"Warning: Icon mapping already exists for '{k}'")
        QTA_MAPPING[k] = v_new


def update_styles(mapping: ty.Dict[str, str], append: bool = True) -> None:
    """Update icon mapping."""
    global STYLES

    if append:
        STYLES.update(mapping)
    else:
        mapping.update(STYLES)
        STYLES = mapping


def update_icons(mapping: ty.Dict[str, str], append: bool = True) -> None:
    """Update icon mapping."""
    global ICONS

    if append:
        ICONS.update(mapping)
    else:
        mapping.update(ICONS)
        ICONS = mapping


def get_icon(name: str | tuple[str, dict]) -> tuple[str, dict]:
    """Return icon."""
    kwargs = None
    if isinstance(name, tuple):
        name, kwargs = name
    if kwargs is None:
        kwargs = {}

    original_name = name
    if name == "":
        name = QTA_MAPPING[MISSING]
    elif "." not in name:
        name = QTA_MAPPING.get(name)
        if name is None:
            logger.warning(f"Failed to retrieve icon: '{original_name}'")
            name = QTA_MAPPING[MISSING]
    if isinstance(name, tuple):
        name, kwargs_ = name
        kwargs.update(kwargs_)
    return name, kwargs


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
    try:
        for key in sorted(STYLES):
            file = STYLES[key]
            with open(file) as f:
                stylesheet += f.read()
        if extra:
            for file in extra:
                with open(file) as f:
                    stylesheet += f.read()
    except FileNotFoundError as e:
        logger.error(f"Failed to load stylesheet: {e}")

    if theme:
        from qtextra.config.theme import THEMES
        from qtextra.utils.template import template

        return template(stylesheet, **THEMES.get_theme(theme, as_dict=True))
    return stylesheet
