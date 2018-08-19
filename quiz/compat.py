import sys

PY3 = sys.version_info > (3, )
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
