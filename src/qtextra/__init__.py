"""Extra widgets for Qt."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("qtextra")
except PackageNotFoundError:
    __version__ = "uninstalled"

__author__ = "Lukasz G. Migas"
__email__ = "lukas.migas@yahoo.com"
__issue_url__ = "https://github.com/illumion-io/qtextra-issues/issues"
__project_url__ = "https://ionglow.io"
