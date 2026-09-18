from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version(__package__)
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
