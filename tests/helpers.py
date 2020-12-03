import snug


class MockClient:
    def __init__(self, response):
        self.response = response

    def send(self, req):
        self.request = req
        return self.response


class MockAsyncClient:
    def __init__(self, response):
        self.response = response

    async def send(self, req):
        self.request = req
        return self.response


snug.send.register(MockClient, MockClient.send)
snug.send_async.register(MockAsyncClient, MockAsyncClient.send)


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
