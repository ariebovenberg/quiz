"""Root of the quiz API.

The entire public API is available at root level:

   >>> import quiz
   >>> quiz.Schema, quiz.execute, quiz.SelectionError, ...
"""
from .build import *  # noqa
from .execution import *  # noqa
from .schema import *  # noqa
from .types import *  # noqa

from . import build, schema  # isort:skip

# Single-sourcing the version number with poetry:
# https://github.com/python-poetry/poetry/pull/2366#issuecomment-652418094
try:
    __version__ = __import__("importlib.metadata").metadata.version(__name__)
except ModuleNotFoundError:  # pragma: no cover
    __version__ = __import__("importlib_metadata").version(__name__)

__all__ = ["build", "schema"]
