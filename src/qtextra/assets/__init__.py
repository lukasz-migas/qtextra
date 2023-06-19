"""Assets."""
import os.path
import typing as ty
from functools import lru_cache
from glob import glob
from pathlib import Path

from qtextra.utilities import get_module_path

HERE = Path(get_module_path("qtextra.assets", "__init__.py")).parent

LOADING_SQUARE_GIF = str(HERE / "loading-square.gif")
LOADING_CIRCLE_GIF = str(HERE / "loading-circle.gif")

QTA_MAPPING: ty.Dict[str, str] = {
    "MISSING": "ri.error-warning-line",
}


def get_icon(name: str):
    """Return icon."""
    if "." not in name:
        name = QTA_MAPPING.get(name)
        if name is None:
            name = QTA_MAPPING["MISSING"]
    return name


@lru_cache(maxsize=12)
def get_stylesheet(theme: str = None, extra: ty.Optional[ty.List[str]] = None) -> str:
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
    resources_dir = os.path.abspath(os.path.dirname(__file__))
    stylesheet = ""
    for file in sorted(glob(os.path.join(resources_dir, "styles", "*.qss"))):
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
