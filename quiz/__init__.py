"""Root of the quiz API.

The entire public API is available at root level:

   >>> import quiz
   >>> quiz.Schema, quiz.execute, quiz.SelectionError, ...
"""
from .__about__ import *  # noqa
from .build import *  # noqa
from .execution import *  # noqa
from .schema import *  # noqa
from .types import *  # noqa

from . import build, schema  # isort:skip

__all__ = ["build", "schema"]
