"""Themes configuration file."""

import re
import typing as ty
from functools import lru_cache
from itertools import product
from pathlib import Path

import numpy as np
from koyo.timer import MeasureTimer
from loguru import logger
from psygnal._evented_model import EventedModel
from pydantic import PrivateAttr, ValidationError, validator
from pydantic.color import Color
from qtpy.QtCore import QDateTime, QTime, Signal
from qtpy.QtGui import QColor, QPalette
from qtpy.QtWidgets import QApplication, QWidget

from qtextra.config.config import ConfigBase, _get_previous_configs
from qtextra.utils.appdirs import USER_CACHE_DIR

DARK_THEME = {
    "name": "dark",
    "type": "dark",
    "background": "rgb(38, 41, 48)",
    "foreground": "rgb(65, 72, 81)",
    "primary": "rgb(90, 98, 108)",
    "secondary": "rgb(189, 147, 249)",
    "highlight": "rgb(106, 115, 128)",
    "text": "rgb(240, 241, 242)",
    "icon": "rgb(209, 210, 212)",
    "warning": "rgb(255, 105, 60)",
    "error": "rgb(183, 52, 53)",
    "success": "rgb(30, 215, 96)",
    "progress": "rgb(179, 98, 0)",
    "current": "rgb(0, 122, 204)",
    "syntax_style": "native",
    "console": "rgb(0, 0, 0)",
    "canvas": "rgb(0, 0, 0)",
    "standout": "rgb(255, 255, 0)",
    "font_size": "14pt",
    "header_size": "18pt",
}
LIGHT_THEME = {
    "name": "light",
    "type": "light",
    "background": "rgb(239, 235, 233)",
    "foreground": "rgb(214, 208, 206)",
    "primary": "rgb(188, 184, 181)",
    "secondary": "rgb(190, 185, 183)",
    "highlight": "rgb(163, 158, 156)",
    "text": "rgb(59, 58, 57)",
    "icon": "rgb(107, 105, 103)",
    "warning": "rgb(255, 105, 60)",
    "error": "rgb(255, 18, 31)",
    "success": "rgb(30, 215, 96)",
    "progress": "rgb(255, 175, 77)",
    "current": "rgb(30, 215, 96)",
    "syntax_style": "default",
    "console": "rgb(255, 255, 255)",
    "canvas": "rgb(255, 255, 255)",
    "standout": "rgb(255, 252, 0)",
    "font_size": "14pt",
    "header_size": "18pt",
}


def time_to_qt_time(value: str) -> QTime:
    """Parse config time to QTime format."""
    time = QTime()
    try:
        _, _ = value.split(":")
    except Exception:
        return time
    time = time.fromString(value, "HH:mm")
    return time


def parse_time(value: str) -> ty.Tuple[int, ...]:
    """Parse time."""
    try:
        hh, mm = value.split(":")
        return int(hh), int(mm)
    except Exception:
        return -1, -1


class CanvasTheme(EventedModel):
    """Plot theme model."""

    canvas: Color
    line: Color
    scatter: Color
    highlight: Color
    axis: Color
    gridlines: Color
    label: Color
    _canvas_backup: ty.Optional[Color] = PrivateAttr(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._canvas_backup = self.canvas

    def as_array(self, name: str) -> np.ndarray:
        """Return color array."""
        return np.asarray(getattr(self, name))


class CanvasThemes(ConfigBase):
    """Plot theme class."""

    # event emitted whenever a theme is changed
    evt_theme_changed = Signal()

    def __init__(self):
        super().__init__(None)
        self.themes = {}
        self._theme = "light"
        self._integrate_canvas: bool = False

        self.add_theme(
            "dark",
            CanvasTheme(
                canvas="black",
                line="white",
                scatter="white",
                highlight="yellow",
                axis="white",
                gridlines="white",
                label="lightgray",
            ),
        )
        self.add_theme(
            "light",
            CanvasTheme(
                canvas="white",
                line="black",
                scatter="black",
                highlight="yellow",
                axis="black",
                gridlines="black",
                label="black",
            ),
        )

        for theme in self.themes.values():
            theme.events.connect(lambda _: self.evt_theme_changed.emit())

    @property
    def integrate_canvas(self):
        """Integrate canvas with background color."""
        return self._integrate_canvas

    @integrate_canvas.setter
    def integrate_canvas(self, value):
        self._integrate_canvas = value
        background = THEMES.active.background if value else self.active._canvas_backup
        self.active.canvas = background

    def add_theme(self, name: str, theme_data: ty.Union[CanvasTheme, ty.Dict[str, str]]):
        """Add theme."""
        if isinstance(theme_data, CanvasTheme):
            self.themes[name] = theme_data
        else:
            self.themes[name] = CanvasTheme(**theme_data)

    def available_themes(self) -> ty.Tuple[str, ...]:
        """Get list of available themes."""
        return tuple(self.themes)

    @property
    def active(self) -> CanvasTheme:
        """Return active theme."""
        return self.themes[self.theme]

    @property
    def theme(self) -> str:
        """Return theme name."""
        return self._theme

    @theme.setter
    def theme(self, value: str):
        if self._theme == value:
            return
        if value not in self.themes:
            return
        self._theme = value
        self.integrate_canvas = self._integrate_canvas
        self.evt_theme_changed.emit()

    def as_array(self, name: str) -> np.ndarray:
        """Return color array."""
        from napari.utils.colormaps.standardize_color import transform_color

        color: Color = getattr(self.active, name)
        return transform_color(color.as_hex())[0]

    def as_hex(self, name: str) -> str:
        """Return color as hex."""
        color: Color = getattr(self.active, name)
        return color.as_hex()


class Theme(EventedModel):
    """Theme model.

    Attributes
    ----------
    name : str
        Name of the virtual folder where icons will be saved to.
    syntax_style : str
        Name of the console style.
        See for more details: https://pygments.org/docs/styles/
    canvas : Color
        Background color of the canvas.
    background : Color
        Color of the application background.
    foreground : Color
        Color to contrast with the background.
    primary : Color
        Color used to make part of a widget more visible.
    secondary : Color
        Alternative color used to make part of a widget more visible.
    highlight : Color
        Color used to highlight visual element.
    text : Color
        Color used to display text.
    warning : Color
        Color used to indicate something is wrong.
    current : Color
        Color used to highlight Qt widget.
    """

    class Config:
        """Pydantic config."""

        validate_assignment = True

    name: str
    type: str
    syntax_style: str
    canvas: Color
    console: Color
    background: Color
    foreground: Color
    primary: Color
    secondary: Color
    highlight: Color
    text: Color
    icon: Color
    warning: Color
    error: Color
    success: Color
    current: Color
    progress: Color
    standout: Color
    font_size: str = "14pt"
    header_size: str = "18pt"

    def __getattr__(self, item: str) -> ty.Any:
        return getattr(self, item)

    @validator(
        "canvas",
        "console",
        "background",
        "foreground",
        "primary",
        "secondary",
        "highlight",
        "text",
        "icon",
        "warning",
        "error",
        "success",
        "current",
        "progress",
        "standout",
        pre=True,
        allow_reuse=True,
    )
    def _validate_color(cls, value) -> Color:
        if isinstance(value, np.ndarray):
            value = value.tolist()
        elif isinstance(value, str):
            value = Color(value).as_hex()
        return Color(value)

    @validator("syntax_style", pre=True, allow_reuse=True)
    def _ensure_syntax_style(value: str) -> str:
        from pygments.styles import STYLE_MAP

        assert (
            value in STYLE_MAP
        ), f"Incorrect `syntax_style` value provided. Please use one of the following: {', '.join(STYLE_MAP)}"
        return value

    @validator("font_size", "header_size", pre=True, allow_reuse=True)
    def _ensure_font_size(value: ty.Union[int, str]) -> str:
        if isinstance(value, int):
            value = str(value)
        value = value.replace("px", "").replace("pt", "")
        if not value.endswith("pt"):
            return value + "pt"
        return value

    @property
    def id(self) -> str:
        """Return theme id."""
        return self.name

    def to_dict(self) -> dict:
        """Export as dictionary."""
        data = {}
        for key, value in self:
            if isinstance(value, Color):
                data[key] = value.as_hex()
            else:
                data[key] = value
        return data


class Themes(ConfigBase):
    """Themes."""

    DEFAULT_CONFIG_NAME = "themes-config.json"
    DEFAULT_CONFIG_GROUPS = ("settings",)
    EXTRA_CONFIG_GROUPS = ("themes",)

    REQUIRED_KEYS = (
        "name",  # name of the theme so the icons can be placed there
        "type",  # type of theme - either dark or light
        "background",  # background color
        "foreground",  # foreground color
        "primary",  # primary color for highlights
        "secondary",  # secondary color for less intense highlights
        "highlight",  # highlight color
        "text",  # color of text
        "icon",  # color of icons
        "warning",  # color of warning
        "error",  # color of error
        "success",  # color of success
        "progress",  # color of progress
        "current",  # color of current item
        "syntax_style",  # used by console
        "console",  # used by console
        "canvas",  # color of the canvas
        "standout",  # standout color
    )

    # event emitted whenever a new theme is added
    evt_theme_added = Signal()
    # event emitted whenever a theme is changed
    evt_theme_changed = Signal()
    # event emitted whenever user changed time check
    evt_update_timer = Signal()
    # event emitted whenever icon color is changed
    evt_theme_icon_changed = Signal()
    # event emitted whenever stylesheets are changed
    evt_qss_changed = Signal()

    def __init__(self):
        super().__init__(None)

        self._theme: str = "light"
        self._sync_with_time: bool = True
        self._light_start_time: str = "08:00"
        self._light_end_time: str = "20:00"
        self.themes: ty.Dict[str, Theme] = {}
        self.add_theme(
            "dark",
            Theme(**DARK_THEME),
        )
        self.add_theme(
            "light",
            Theme(**LIGHT_THEME),
        )
        # synchronize our icon with napari icon color
        try:
            from napari.utils.theme import _themes

            for name in _themes:
                _themes[name].icon = self.get_hex_color("icon")
        except ImportError:
            pass

        for theme in self.themes.values():
            theme.events.connect(lambda _: self.evt_theme_changed.emit())

    def __getitem__(self, item):
        return self.themes[item]

    @property
    def active(self) -> Theme:
        """Return active theme."""
        return self.themes[self.theme]

    def get_sync_theme(self) -> str:
        """Get theme based on synchronization settings."""
        curr_time: QTime = QDateTime.currentDateTime().time()
        start_time = time_to_qt_time(self.light_start_time)
        end_time = time_to_qt_time(self.light_end_time)
        if start_time <= curr_time <= end_time:
            return "light"
        return "dark"

    def synchronize_theme(self) -> None:
        """Synchronize theme."""
        if self.sync_with_time:
            theme = self.get_sync_theme()
            self.theme = theme

    @property
    def sync_with_time(self) -> bool:
        """Flag to indicate whether theme should be synchronized with time."""
        return self._sync_with_time

    @sync_with_time.setter
    def sync_with_time(self, value: bool):
        self._sync_with_time = value
        self.evt_update_timer.emit()

    @property
    def light_start_time(self) -> str:
        """Get morning time."""
        return self._light_start_time

    @light_start_time.setter
    def light_start_time(self, value: str) -> None:
        self._light_start_time = value
        self.synchronize_theme()

    @property
    def light_end_time(self) -> str:
        """Get evening time."""
        return self._light_end_time

    @light_end_time.setter
    def light_end_time(self, value: str) -> None:
        self._light_end_time = value
        self.synchronize_theme()

    @property
    def theme(self) -> str:
        """Get theme."""
        return self._theme

    @theme.setter
    def theme(self, value: str) -> None:
        """Set theme."""
        if self._theme == value:
            return
        self._theme = value
        # synchronize our icon with napari icon color
        try:
            from napari.utils.theme import _themes

            for name in _themes:
                _themes[name].icon = self.get_hex_color("icon")
        except ImportError:
            pass
        with MeasureTimer() as timer:
            self.evt_theme_changed.emit()
            self.evt_theme_icon_changed.emit()
        logger.debug(f"Changed theme to '{value}' in {timer()}")

    def update_palette(self) -> None:
        """Get updated palette."""
        qapp = QApplication.instance()
        if qapp is None:
            return
        palette = qapp.palette()
        palette.setColor(QPalette.ColorRole.Link, QColor("#f56833"))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor("#f56833"))
        qapp.setPalette(palette)

    @property
    def syntax_style(self) -> str:
        """Get syntax style."""
        return self.active.syntax_style

    def get_font_size(self) -> int:
        """Get font size."""
        unit = "pt" if "pt" in self.active.font_size else "px"
        return int(self.active.font_size.split(unit)[0])

    def get_rgb_color(self, name: str) -> str:
        """Get color in the default style."""
        color: Color = getattr(self.active, name)
        return color.as_rgb()

    def get_hex_color(self, name: str) -> str:
        """Get color in hex format."""
        color: Color = getattr(self.active, name)
        return color.as_hex()

    def get_qt_color(self, name: str) -> QColor:
        """Get QColor."""
        color = self.get_hex_color(name)
        return QColor(color)

    @staticmethod
    def get_text_color_for_background(color: str) -> str:
        """Get text color for background."""
        from qtextra.utils.color import get_text_color, rgb_to_hex

        color = QColor(color)
        return rgb_to_hex(get_text_color(color).getRgb())

    def get_theme(
        self, theme_name: ty.Optional[str] = None, as_dict: bool = False
    ) -> ty.Union[Theme, ty.Dict[str, str]]:
        """Get a theme based on its name.

        Parameters
        ----------
        theme_name : str
            Name of requested theme.
        as_dict : bool
            Flag to return as dictionary.

        Returns
        -------
        theme: dict of str: str
            Theme mapping elements to colors. A copy is created
            so that manipulating this theme can be done without
            side effects.
        """
        if theme_name is None:
            theme_name = self.theme
        if theme_name in self.themes:
            theme = self.themes[theme_name]
            _theme = theme.copy()
            if as_dict:
                return _theme.dict()
            return _theme
        else:
            raise ValueError(f"Unrecognized theme {theme_name}. Available themes are {self.available_themes()}")

    @property
    def is_dark(self) -> bool:
        """Check if theme is dark."""
        return self.active.type == "dark"

    def add_theme(self, name: str, theme_data: ty.Union[Theme, ty.Dict[str, str]], register: bool = False):
        """Add theme."""
        if name not in self.themes:
            self.add_resource(name)
        if isinstance(theme_data, dict):
            theme_data = Theme(**theme_data)

        self.themes[name] = theme_data
        self.themes[name].events.icon.connect(lambda _: self._emit_icon_color_change(name))
        if register:
            self.register_themes([name])

    def add_resource(self, name: str):
        """Add resources to QDir."""
        from qtpy.QtCore import QDir

        QDir.addSearchPath(f"theme_{name}", str(self.get_theme_path(name)))
        logger.debug(f"Added '{name}' theme to resources path")

    def register_themes(self, names: ty.Optional[ty.List[str]] = None) -> None:
        """Register themes."""
        from qtextra.icons import build_theme_svgs

        if names is None:
            names = list(self.themes.keys())

        for name in names:
            build_theme_svgs(name)

    def available_themes(self) -> ty.Tuple[str, ...]:
        """Get list of available themes."""
        return tuple(self.themes)

    def get_theme_color(self, theme_name: ty.Optional[str] = None, key: str = "text") -> str:
        """Get text color appropriate for the theme."""
        if theme_name is None:
            theme_name = self.theme
        palette = self.themes[theme_name]
        return getattr(palette, key).as_hex()

    def get_theme_stylesheet(self, theme_name: ty.Optional[str] = None) -> str:
        """Get stylesheet."""
        from qtextra.assets import get_stylesheet
        from qtextra.utils.template import template

        if theme_name is None:
            theme_name = self.theme
        palette = self.themes[theme_name].dict()
        stylesheet = get_stylesheet()
        stylesheet = template(stylesheet, **palette)
        return stylesheet

    def set_theme_stylesheet(self, widget: QWidget, theme_name: ty.Optional[str] = None) -> None:
        """Set stylesheet on widget."""
        widget.setStyleSheet(self.get_theme_stylesheet(theme_name))

    @staticmethod
    def get_theme_path(theme_name: str) -> Path:
        """Get path of directory for a given theme name."""
        from qtextra.utils.appdirs import USER_THEME_DIR

        return USER_THEME_DIR / theme_name

    def _get_config_parameters(self, config: ty.Dict) -> ty.Dict:
        """Get configuration parameters."""
        config["themes"] = {}
        for name, theme in self.themes.items():
            config["themes"][name] = theme.to_dict()
        config["settings"] = {
            "theme": self.theme,
            "sync_with_time": self._sync_with_time,
            "light_start_time": self._light_start_time,
            "light_end_time": self._light_end_time,
        }
        return config

    def _emit_icon_color_change(self, name: str) -> None:
        """Emit icon color change event."""
        self.register_themes([name])
        self.evt_theme_icon_changed.emit()
        logger.debug(f"Updating icon color for '{name}'...")

    def _set_config_parameters(self, config: ty.Dict) -> None:
        """Set extra configuration parameters."""
        for config_group_title in ("themes",):
            _config_group = config.get(config_group_title, {})
            for theme_name, theme in _config_group.items():
                try:
                    if theme_name in self.themes:
                        for key, value in theme.items():
                            try:
                                setattr(self.themes[theme_name], key, value)
                            except ValidationError as err:
                                logger.warning(
                                    f"Failed setting of {key} because it did not pass validation."
                                    f"\nFailed with error=`{err}`"
                                )
                    else:
                        theme = Theme(**theme)
                        theme.events.icon.connect(lambda _: self._emit_icon_color_change(theme_name))  # noqa: B023
                        self.themes[theme_name] = theme
                except ValidationError as err:
                    logger.warning(
                        f"Skipping {theme_name} theme because it did not pass validation.\nFailed with error=`{err}`"
                    )
                except Exception:
                    logger.warning("Could not load theme data.")

    def lighten(self, color: str, percentage: float = 10, as_hex: bool = False) -> str:
        """Lighted color."""
        from qtextra.utils.template import lighten

        color = lighten(color, percentage)
        if as_hex:
            color = Color(color).as_hex()
        return color

    def darken(self, color: str, percentage: float = 10, as_hex: bool = False) -> str:
        """Lighted color."""
        from qtextra.utils.template import darken

        color = darken(color, percentage)
        if as_hex:
            color = Color(color).as_hex()
        return color


def get_previous_configs(base_dir: ty.Optional[str] = None, filename: str = "themes-config.json") -> ty.Dict[str, str]:
    """Return dictionary of version : path of previous configuration files."""
    return _get_previous_configs(base_dir, filename)


svg_elem = re.compile(r"(<svg[^>]*>)")
svg_style = """<style type="text/css">
path {{fill: {0}; opacity: {1};}}
polygon {{fill: {0}; opacity: {1};}}
circle {{fill: {0}; opacity: {1};}}
rect {{fill: {0}; opacity: {1};}}
</style>"""


def get_theme_cache_dir(theme_name: str) -> Path:
    """Get theme cache directory."""
    return Path(USER_CACHE_DIR) / "_themes" / theme_name


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
    # mapping of svg_stem to theme_key
    theme_override = theme_override or {}

    ALIAS_T = "{color}/{svg_stem}{opacity}.svg"

    for color, path, op in product(colors, svg_paths, opacities):
        clrkey = color
        svg_stem = Path(path).stem
        if isinstance(color, tuple):
            clrkey, theme_key = color
            theme_key = theme_override.get(svg_stem, theme_key)
            color = getattr(THEMES.get_theme(clrkey, False), theme_key).as_hex()
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
):
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
    """Build theme SVGs."""
    from qtextra.assets import ICONS

    out = get_theme_cache_dir(theme_name)
    write_colorized_svgs(
        out,
        svg_paths=ICONS.values(),
        colors=[(theme_name, "icon")],
        opacities=(0.5, 1),
        theme_override={"warning": "warning", "logo_silhouette": "background"},
    )
    return str(out)


def is_dark() -> bool:
    """Check if theme is dark."""
    return THEMES.is_dark


THEMES: Themes = Themes()
THEMES.register_themes()
CANVAS: CanvasThemes = CanvasThemes()
