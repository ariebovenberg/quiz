import sys

PY3 = sys.version_info > (3, )
PY2 = not PY3


if PY3:
    from functools import singledispatch
    from textwrap import indent
else:
    from singledispatch import singledispatch  # noqa

    def indent(text, pad):
        return '\n'.join(map(pad.__add__, text.splitlines()))
