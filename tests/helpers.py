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
