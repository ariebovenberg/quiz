# -*- coding: utf-8 -*-
from textwrap import dedent

import pytest
import six
from hypothesis import given, strategies

import quiz
from quiz import SELECTOR as _
from quiz import Field, InlineFragment, SelectionSet, gql
from quiz.utils import FrozenDict as fdict

from .example import Dog
from .helpers import AlwaysEquals, NeverEquals


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

    class TestGQL:

        def test_empty(self):
            assert gql(Field('foo')) == 'foo'

        def test_arguments(self):
            field = Field('foo', {
                'foo': 4,
                'blabla': 'my string!',
            })

            # arguments are unordered, multiple valid options
            assert gql(field) in [
                'foo(foo: 4, blabla: "my string!")',
                'foo(blabla: "my string!", foo: 4)',
            ]

        def test_alias(self):
            field = Field('foo', {
                'a': 4,
            }, alias='my_alias')
            assert gql(field) == 'my_alias: foo(a: 4)'

        def test_selection_set(self):
            field = Field('bla', fdict({'q': 9}), selection_set=SelectionSet(
                Field('blabla'),
                Field('foobar', fdict({'qux': 'another string'})),
                Field('other', selection_set=SelectionSet(
                    Field('baz'),
                )),
                InlineFragment(
                    on=Dog,
                    selection_set=SelectionSet(
                        Field('name'),
                        Field('bark_volume'),
                        Field('owner', selection_set=SelectionSet(
                            Field('name'),
                        ))
                    )
                ),
            ))
            assert gql(field) == dedent('''
            bla(q: 9) {
              blabla
              foobar(qux: "another string")
              other {
                baz
              }
              ... on Dog {
                name
                bark_volume
                owner {
                  name
                }
              }
            }
            ''').strip()


class TestSelectionSet:

    def test_empty(self):
        assert _ == SelectionSet()

    def test_hash(self):
        assert hash(SelectionSet()) == hash(SelectionSet())
        assert hash(_.foo.bar) == hash(_.foo.bar)
        assert hash(_.bar.foo) != hash(_.foo.bar)

    def test_equality(self):
        instance = _.foo.bar
        assert instance == _.foo.bar
        assert not instance == _.bar.foo
        assert instance == AlwaysEquals()
        assert not instance == NeverEquals()

        assert instance != _.bar.foo
        assert not instance != _.foo.bar
        assert instance != NeverEquals()
        assert not instance != AlwaysEquals()

    def test_repr(self):
        instance = _.foo.bar(bla=3)
        rep = repr(instance)
        assert 'SelectionSet' in rep
        assert gql(instance) in rep

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

    class TestGetItem:

        def test_simple(self):
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

        def test_empty(self):
            with pytest.raises(quiz.utils.Empty):
                _['bla']

        def test_nested(self):
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

    class TestCall:

        def test_simple(self):
            assert _.foo(bla=4, bar=None) == SelectionSet(
                Field('foo', {'bla': 4, 'bar': None}),
            )

        def test_empty(self):
            assert _.foo() == SelectionSet(Field('foo'),)

        def test_argument_named_self(self):
            assert _.foo(self=4, bla=3) == SelectionSet(
                Field('foo', fdict({'self': 4, 'bla': 3})))

        def test_invalid(self):
            with pytest.raises(quiz.utils.Empty):
                _()

        def test_alias(self):
            assert _('foo').bla(a=4) == SelectionSet(
                Field('bla', {'a': 4}, alias='foo')
            )

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
                          Field('height', fdict({'unit': 'cm'})),
                      )),
                Field('oof'),
                Field('qux'),
            ))
        )


class TestArgumentAsGql:

    def test_string(self):
        assert quiz.argument_as_gql('foo\nb"ar') == '"foo\\nb\\"ar"'

    def test_invalid(self):
        class MyClass(object):
            pass
        with pytest.raises(TypeError, match='MyClass'):
            quiz.argument_as_gql(MyClass())

    def test_int(self):
        assert quiz.argument_as_gql(4) == '4'

    def test_none(self):
        assert quiz.argument_as_gql(None) == 'null'

    def test_bool(self):
        assert quiz.argument_as_gql(True) == 'true'
        assert quiz.argument_as_gql(False) == 'false'

    @pytest.mark.parametrize('value, expect', [
        (1.2, '1.2'),
        (1., '1.0'),
        (1.234e53, '1.234e+53'),
    ])
    def test_float(self, value, expect):
        assert quiz.argument_as_gql(value) == expect

    def test_enum(self):

        class MyEnum(quiz.Enum):
            FOO = 'FOOVALUE'
            BLA = 'QUX'

        assert quiz.argument_as_gql(MyEnum.BLA) == 'QUX'


class TestEscape:

    def test_empty(self):
        assert quiz.escape('') == ''

    @pytest.mark.parametrize('value', [
        'foo',
        '   bla   ',
        ' some words-here ',
    ])
    def test_no_escape_needed(self, value):
        assert quiz.escape(value) == value

    @pytest.mark.parametrize('value, expect', [
        ('foo\nbar', 'foo\\nbar'),
        ('"quoted" --', '\\"quoted\\" --'),
        ('foøo', 'foøo'),
    ])
    def test_escape_needed(self, value, expect):
        assert quiz.escape(value) == expect

    @given(strategies.text())
    def test_fuzzing(self, value):
        assert isinstance(quiz.escape(value), six.text_type)
