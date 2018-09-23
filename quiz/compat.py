import sys

PY3 = sys.version_info > (3, )
HAS_PEP519 = sys.version_info > (3, 6)
PY2 = not PY3


if PY3:
    from functools import singledispatch
    from textwrap import indent
    map = map
else:  # pragma: no cover
    from singledispatch import singledispatch  # noqa

    def indent(text, pad):
        return '\n'.join(map(pad.__add__, text.splitlines()))

    from itertools import imap as map


if HAS_PEP519:
    from os import fspath
else:  # pragma: no cover
    # code adapted from https://www.python.org/dev/peps/pep-0519/
    def fspath(path):
        # type: Union[Pathlike, str, bytes] -> Union[str, bytes]
        """Return the string representation of the path.

        If str or bytes is passed in, it is returned unchanged. If __fspath__()
        returns something other than str or bytes then TypeError is raised. If
        this function is given something that is not str, bytes, or os.PathLike
        then TypeError is raised.
        """
        if isinstance(path, (str, bytes)):
            return path

        # Work from the object's type to match method resolution of other magic
        # methods.
        path_type = type(path)
        try:
            path = path_type.__fspath__(path)
        except AttributeError:
            if hasattr(path_type, '__fspath__'):
                raise
        else:
            if isinstance(path, (str, bytes)):
                return path
            else:
                raise TypeError(
                    "expected __fspath__() to return str or bytes, "
                    "not " + type(path).__name__)

        raise TypeError("expected str, bytes or os.PathLike object, not "
                        + path_type.__name__)
