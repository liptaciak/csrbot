"""Core components."""

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

from .core import (
    StringEnum,
    # string_enum,
)
try:
    del core
except NameError:
    pass
