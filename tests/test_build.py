import pytest

from quiz.build import Field, SelectionSet, NestedObject, Error, gql
from quiz.build import field_chain as _


class TestField:

    def test_defaults(self):
        f = Field('foo')
        assert f.kwargs == {}

    def test_hash(self):
        assert hash(Field('foo', {'bar': 3})) == hash(Field('foo', {'bar': 3}))
        assert hash(Field('bla', {'bla': 4})) != hash(Field('bla'))

    @pytest.mark.parametrize('field, expect', [
        (Field('foo'), 'foo'),
        (Field('bla', {'boo': 9}), 'bla(boo: 9)')
    ])
    def test_gql(self, field, expect):
        assert gql(field) == expect


class TestFieldChain:

    def test_empty(self):
        assert _ == SelectionSet()

    def test_hash(self):
        assert hash(SelectionSet()) == hash(SelectionSet())
        assert hash(_.foo.bar) == hash(_.foo.bar)
        assert hash(_.bar.foo) != hash(_.foo.bar)

    def test_getattr(self):
        assert _.foo_field.bla == SelectionSet(
            Field('foo_field'),
            Field('bla'),
        )

    def test_iter(self):
        items = (
            Field('foo'),
            Field('bar'),
        )
        assert tuple(SelectionSet(*items)) == items
        assert len(SelectionSet(*items)) == 2

    def test_getitem(self):
        assert _.foo.bar.blabla[
            _
            .foobar
            .bing
        ] == SelectionSet(
            Field('foo'),
            Field('bar'),
            NestedObject(
                Field('blabla'),
                (
                    Field('foobar'),
                    Field('bing'),
                )
            )
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
        ] == SelectionSet(
            NestedObject(
                Field('foo'),
                (
                    Field('bar'),
                    NestedObject(
                        Field('bing'),
                        (
                            Field('blabla'),
                        )
                    )
                )
            )
        )

    def test_call(self):
        assert _.foo(bla=4, bar=None) == SelectionSet(
            Field('foo', {'bla': 4, 'bar': None}),
        )

    def test_call_empty(self):
        assert _.foo() == SelectionSet(
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
        ] == SelectionSet(
            Field('foo', {}),
            NestedObject(
                Field('bar'),
                (
                    Field('bing', {'param1': 4.1}),
                    Field('baz'),
                    NestedObject(
                        Field('foo_bar_bla', {'p2': None, 'r': ''}),
                        (
                            Field('height', {'unit': 'cm'}),
                        )
                    ),
                    Field('oof'),
                    Field('qux'),
                )
            )
        )


class TestSchemaValidation:
    pass
