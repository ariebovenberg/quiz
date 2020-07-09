import pydoc

import snug


def render_doc(obj):
    return pydoc.render_doc(obj, renderer=pydoc.plaintext)


class AlwaysEquals:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class NeverEquals:
    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True


class MockClient:
    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response

    async def send_async(self, req):
        self.request = req
        return self.response


snug.send.register(MockClient, MockClient.send)
