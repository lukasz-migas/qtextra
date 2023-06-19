"""Assets."""
from pathlib import Path

from qtextra.utilities import get_module_path

HERE = Path(get_module_path("qtextra.assets", "__init__.py")).parent
LOADING_SQUARE_GIF = str(HERE / "loading.gif")
LOADING_CIRCLE_GIF = str(HERE / "loading-circle.gif")


def get_icon(name: str) -> str:
    """Return icon."""
    if "." not in name:
        name = QTA_MAPPING.get(name)
        if name is None:
            name = QTA_MAPPING["MISSING"]
    return name


QTA_MAPPING = {
    "MISSING": "ri.error-warning-line",
}
