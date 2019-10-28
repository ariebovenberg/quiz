import inspect

import pytest

from quiz import utils
from quiz.compat import PY3

from .helpers import AlwaysEquals, NeverEquals


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


class TestValueObject:
    def test_simple(self):
        class MyBase:
            pass

        class Foo(MyBase, utils.ValueObject):
            """my foo class"""

            __fields__ = [
                ("foo", int, "the foo"),
                ("bla", str, "description for bla"),
            ]

        assert Foo.__doc__ == "my foo class"
        assert issubclass(Foo, utils.ValueObject)
        assert issubclass(Foo, MyBase)

        if PY3:
            Foo.__qualname__ = "my_module.Foo"
            assert inspect.signature(Foo) == inspect.signature(
                Foo.__namedtuple_cls__
            )

        instance = Foo(4, bla="foo")

        assert instance == Foo(4, bla="foo")
        assert not instance == Foo(4, bla="blabla")
        assert instance == AlwaysEquals()
        assert not instance == NeverEquals()

        assert instance != Foo(4, bla="blabla")
        assert not instance != Foo(4, bla="foo")
        assert instance != NeverEquals()
        assert not instance != AlwaysEquals()

        assert instance.replace(foo=5) == Foo(5, bla="foo")
        assert instance.replace() == instance

        assert hash(instance) == hash(instance.replace())
        assert hash(instance) != hash(instance.replace(foo=5))

        assert instance.foo == 4
        assert instance.bla == "foo"

        with pytest.raises(AttributeError, match="blabla"):
            instance.blabla

        with pytest.raises(AttributeError, match="can't set"):
            instance.foo = 6

        if PY3:
            assert repr(instance) == "my_module.Foo(foo=4, bla='foo')"
        else:
            assert repr(instance) == "Foo(foo=4, bla='foo')"

        assert Foo.bla.__doc__ == "description for bla"

        # repr should never fail, even if everything is wrong
        del instance._values
        repr(instance)

    def test_defaults(self):
        class Foo(utils.ValueObject):
            __fields__ = [
                ("foo", int, "the foo"),
                ("bla", str, "the bla"),
                ("qux", float, "another field!"),
            ]
            __defaults__ = ("", 1.0)

        assert Foo(4) == Foo(4, "", 1.0)
        assert Foo(4, "bla", 1.1) == Foo(4, "bla", 1.1)
