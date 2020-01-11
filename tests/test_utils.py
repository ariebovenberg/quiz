import pytest
from quiz import utils


class TestMergeMappings:
    def test_empty(self):
        assert utils.merge() == {}

    def test_single(self):
        assert utils.merge({"foo": 4}) == {"foo": 4}

    def test_multiple(self):
        result = utils.merge(
            utils.FrozenDict({"foo": 5}), {"foo": 9, "bla": 2}, {"blabla": 1}
        )
        assert isinstance(result, utils.FrozenDict)
        assert result == {"foo": 9, "bla": 2, "blabla": 1}


class TestInitList:
    def test_simple(self):
        assert utils.init_last([1, 2, 3, 4, 5]) == ([1, 2, 3, 4], 5)

    def test_empty(self):
        with pytest.raises(utils.Empty):
            utils.init_last([])


class TestCompose:
    def test_empty(self):
        obj = object()
        func = utils.compose()
        assert func(obj) is obj
        assert isinstance(func.funcs, tuple)
        assert func.funcs == ()

    def test_one_func_with_multiple_args(self):
        func = utils.compose(int)
        assert func("10", base=5) == 5
        assert isinstance(func.funcs, tuple)
        assert func.funcs == (int,)

    def test_multiple_funcs(self):
        func = utils.compose(str, lambda x: x + 1, int)
        assert isinstance(func.funcs, tuple)
        assert func("30", base=5) == "16"
