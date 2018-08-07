import pytest

from quiz.build import Field, Selector, Error, gql
from quiz.build import selector as _


class TestField:

    def test_defaults(self):
        f = Field('foo')
        assert f.kwargs == {}
        assert f.selection_set == ()

    def test_hash(self):
        assert hash(Field('foo', {'bar': 3})) == hash(Field('foo', {'bar': 3}))
        assert hash(Field('bla', {'bla': 4})) != hash(Field('bla'))

    @pytest.mark.parametrize('field, expect', [
        (Field('foo'), 'foo'),
        (Field('bla', {'boo': 9}), 'bla(boo: 9)')
    ])
    def test_gql(self, field, expect):
        assert gql(field) == expect


class TestSelector:

    def test_empty(self):
        assert _ == Selector()

    def test_hash(self):
        assert hash(Selector()) == hash(Selector())
        assert hash(_.foo.bar) == hash(_.foo.bar)
        assert hash(_.bar.foo) != hash(_.foo.bar)

    def test_getattr(self):
        assert _.foo_field.bla == Selector(
            Field('foo_field'),
            Field('bla'),
        )

    def test_iter(self):
        items = (
            Field('foo'),
            Field('bar'),
        )
        assert tuple(Selector(*items)) == items
        assert len(Selector(*items)) == 2

    def test_getitem(self):
        assert _.foo.bar.blabla[
            _
            .foobar
            .bing
        ] == Selector(
            Field('foo'),
            Field('bar'),
            Field('blabla', selection_set=(
                Field('foobar'),
                Field('bing'),
            ))
        )

    def test_getitem_empty(self):
        with pytest.raises(Error):
            _['bla']

    def test_getitem_nested(self):
        assert _.foo[
            _
            .bar
            .bing[
                _
                .blabla
            ]
        ] == Selector(
            Field('foo', selection_set=(
                Field('bar'),
                Field('bing', selection_set=(
                    Field('blabla'),
                ))
            ))
        )

    def test_call(self):
        assert _.foo(bla=4, bar=None) == Selector(
            Field('foo', {'bla': 4, 'bar': None}),
        )

    def test_call_empty(self):
        assert _.foo() == Selector(
            Field('foo'),
        )

    def test_invalid_call(self):
        with pytest.raises(Error):
            _()

    def test_combination(self):
        assert _.foo.bar[
            _
            .bing(param1=4.1)
            .baz
            .foo_bar_bla(p2=None, r='')[
                _
                .height(unit='cm')
            ]
            .oof
            .qux()
        ] == Selector(
            Field('foo'),
            Field('bar', selection_set=(
                Field('bing', {'param1': 4.1}),
                Field('baz'),
                Field('foo_bar_bla', {'p2': None, 'r': ''}, selection_set=(
                    Field('height', {'unit': 'cm'}),
                )),
                Field('oof'),
                Field('qux'),
            ))
        )


class TestSchemaValidation:
    pass
