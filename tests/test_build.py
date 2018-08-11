import pytest

from quiz.types import Field, SelectionSet, Error, gql, SelectionSet
from quiz.types import selector as _
from quiz.utils import FrozenDict as fdict


class TestField:

    def test_defaults(self):
        f = Field('foo')
        assert f.kwargs == {}
        assert isinstance(f.kwargs, fdict)
        assert f.selection_set == SelectionSet()
        assert isinstance(f.selection_set, SelectionSet)

    def test_hash(self):
        assert hash(Field('foo', fdict({'bar': 3}))) == hash(
            Field('foo', fdict({'bar': 3})))
        assert hash(Field('bla', fdict({'bla': 4}))) != hash(Field('bla'))

    @pytest.mark.parametrize('field, expect', [
        (Field('foo'), 'foo'),
        (Field('bla', fdict({'boo': 9})), 'bla(boo: 9)')
    ])
    def test_gql(self, field, expect):
        assert gql(field) == expect


class TestSelectionSet:

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
            Field('blabla', selection_set=SelectionSet(
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
        ] == SelectionSet(
            Field('foo', selection_set=SelectionSet(
                Field('bar'),
                Field('bing', selection_set=SelectionSet(
                    Field('blabla'),
                ))
            ))
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
            Field('foo'),
            Field('bar', selection_set=SelectionSet(
                Field('bing', fdict({'param1': 4.1})),
                Field('baz'),
                Field('foo_bar_bla',
                      fdict({'p2': None, 'r': ''}),
                      SelectionSet(
                          Field('height', {'unit': 'cm'}),
                      )),
                Field('oof'),
                Field('qux'),
            ))
        )
