"""Root of the quiz API.

The entire public API is available at root level:

   >>> import quiz
   >>> quiz.Schema, quiz.execute, quiz.SelectionError, ...
"""
from .__about__ import (__author__, __copyright__, __description__,  # noqa
                        __version__)
from .build import *  # noqa
from .execution import *  # noqa
from .schema import *  # noqa
from .types import *  # noqa

from . import build, schema  # noqa isort:skip
