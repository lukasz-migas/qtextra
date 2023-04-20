"""Extra widgets for Qt"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("qtextra")
except PackageNotFoundError:
    __version__ = "uninstalled"

__author__ = "Lukasz G. Migas"
__email__ = "lukas.migas@yahoo.com"
