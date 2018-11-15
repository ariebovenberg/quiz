import pydoc

import six
import snug


class MockClient:

    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response


snug.send.register(MockClient, MockClient.send)


class AlwaysEquals:
    """useful for testing correct __eq__, __ne__ implementations"""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class NeverEquals:
    """useful for testing correct __eq__, __ne__ implementations"""

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True


if six.PY3:
    def render_doc(obj):
        return pydoc.render_doc(obj, renderer=pydoc.plaintext)
else:
    def render_doc(obj):
        return pydoc.plain(pydoc.render_doc(obj))
