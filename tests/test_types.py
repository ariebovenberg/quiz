import typing as t
import datetime
from textwrap import dedent

import pytest

import quiz
from quiz import gql, types
from quiz.types import Error, Field, InlineFragment, SelectionSet
from quiz.types import selector as _
from quiz.utils import FrozenDict as fdict

from .example import Command, Dog, Hobby, Query


class TestObjectGetItem:

    def test_valid(self):
        selection_set = (
            _
            .name
            .knows_command(command=Command.SIT)
            .is_housetrained
            .owner[
                _
                .name
                .hobbies[
                    _
                    .name
                    .cool_factor
                ]
            ]
            .best_friend[
                _
                .name
            ]
        )
        fragment = Dog[selection_set]
        assert fragment == types.InlineFragment(Dog, selection_set)

    def test_no_such_field(self):
        with pytest.raises(types.NoSuchField) as exc:
            Dog[
                _
                .name
                .foo
                .knows_command(command=Command.SIT)
            ]
        assert exc.value == types.NoSuchField(Dog, 'foo')

    def test_no_such_argument(self):
        selection_set = _.name(foo=4)
        with pytest.raises(types.NoSuchArgument) as exc:
            Dog[selection_set]
        assert exc.value == types.NoSuchArgument(Dog, Dog.name, 'foo')

    def test_missing_arguments(self):
        selection_set = _.knows_command()
        with pytest.raises(types.MissingArgument) as exc:
            Dog[selection_set]
        assert exc.value == types.MissingArgument(Dog, Dog.knows_command,
                                                  'command')

    def test_invalid_argument_type(self):
        selection_set = _.knows_command(command='foobar')
        with pytest.raises(types.InvalidArgumentType) as exc:
            Dog[selection_set]
        assert exc.value == types.InvalidArgumentType(
            Dog, Dog.knows_command, 'command', 'foobar')  # noqa

    def test_invalid_nested(self):
        with pytest.raises(types.NoSuchField) as exc:
            Dog[_.owner[_.hobbies[_.foo]]]
        assert exc.value == types.NoSuchField(Hobby, 'foo')

    def test_selection_set_on_non_object(self):
        # TODO: maybe a more descriptive error
        with pytest.raises(types.NoSuchField) as exc:
            Dog[_.name[_.foo]]
        assert exc.value == types.NoSuchField(str, 'foo')

    # TODO: check union

    # TODO: check objects always have selection sets


class TestInlineFragment:

    def test_gql(self):
        fragment = Dog[
            _
            .name
            .bark_volume
            .knows_command(command=Command.SIT)
            .is_housetrained
            .owner[
                _
                .name
            ]
        ]
        assert gql(fragment) == dedent('''\
        ... on Dog {
          name
          bark_volume
          knows_command(command: SIT)
          is_housetrained
          owner {
            name
          }
        }
        ''').strip()


class TestQuery:

    def test_valid(self):
        selection_set = (
            _
            .dog[
                _
                .name
                .is_housetrained
            ]
        )
        query = quiz.query(selection_set, cls=Query)
        assert isinstance(query, types.Operation)
        assert query.type is types.OperationType.QUERY  # noqa
        assert len(query.selection_set) == 1

    def test_validation(self):
        with pytest.raises(types.NoSuchField) as exc:
            quiz.query(
                _
                .dog[
                    _
                    .name
                    .is_housetrained
                    .foobar
                ],
                cls=Query,
            )
        assert exc.value == types.NoSuchField(Dog, 'foobar')


class TestOperation:

    def test_graphql(self):
        operation = types.Operation(
            types.OperationType.QUERY,
            SelectionSet(
                types.Field('foo'),
                types.Field('qux', fdict({'buz': 99}), SelectionSet(
                    types.Field('nested'),
                ))
            )
        )
        assert gql(operation) == dedent('''
        query {
          foo
          qux(buz: 99) {
            nested
          }
        }
        ''').strip()


class TestFieldSchema:

    def test_repr(self):
        schema = types.FieldSchema(
            'foo', 'my description', type=t.List[str],
            args=fdict.EMPTY,
            is_deprecated=False, deprecation_reason=None)
        assert types.type_repr(t.List[str]) in repr(schema)


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
            with pytest.raises(Error):
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

        def test_invalid(self):
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
                          Field('height', fdict({'unit': 'cm'})),
                      )),
                Field('oof'),
                Field('qux'),
            ))
        )


class TestArgumentAsGql:

    def test_string(self):
        assert quiz.argument_as_gql("foo") == '"foo"'

    def test_invalid(self):
        class MyClass:
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


class TestRaw:

    def test_gql(self):
        raw = quiz.Raw('my raw graphql')
        assert gql(raw) == 'my raw graphql'
