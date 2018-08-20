from textwrap import dedent

import pytest

import quiz
from quiz import Error, Field, InlineFragment, SelectionSet, gql
from quiz import selector as _
from quiz.utils import FrozenDict as fdict

from .example import Command, Dog, Hobby, Human, Query
from .helpers import AlwaysEquals, NeverEquals


class TestUnion:

    def test_instancecheck(self):

        class MyUnion(quiz.Union):
            __args__ = (str, int)

        assert isinstance('foo', MyUnion)
        assert isinstance(5, MyUnion)
        assert not isinstance(1.3, MyUnion)


class TestOptional:

    def test_instancecheck(self):

        class MyOptional(quiz.Nullable):
            __arg__ = int

        assert isinstance(5, MyOptional)
        assert isinstance(None, MyOptional)
        assert not isinstance(5.4, MyOptional)


class TestList:

    def test_isinstancecheck(self):

        class MyList(quiz.List):
            __arg__ = int

        assert isinstance([1, 2], MyList)
        assert isinstance([], MyList)
        assert not isinstance(['foo'], MyList)
        assert not isinstance([3, 'bla'], MyList)
        assert not isinstance((1, 2), MyList)


class TestValidate:

    def test_empty(self):
        selection = SelectionSet()
        assert quiz.validate(Dog, selection) == SelectionSet()

    def test_simple_valid(self):
        assert quiz.validate(Dog, _.name) == _.name

    def test_complex_valid(self):
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
        assert quiz.validate(Dog, selection_set) == selection_set

    def test_no_such_field(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.name.foo.knows_command(command=Command.SIT))
        assert exc.value == quiz.SelectionError(
            Dog, 'foo', quiz.NoSuchField())

    def test_invalid_argument(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.knows_command(
                foo=1, command=Command.SIT))
        assert exc.value == quiz.SelectionError(
            Dog,
            'knows_command',
            quiz.NoSuchArgument('foo'))

    def test_missing_arguments(self):
        selection_set = _.knows_command
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, selection_set)

        assert exc.value == quiz.SelectionError(
            Dog,
            'knows_command',
            quiz.MissingArgument('command')
        )

    def test_invalid_argument_type(self):
        selection_set = _.knows_command(command='foobar')
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, selection_set)

        assert exc.value == quiz.SelectionError(
            Dog,
            'knows_command',
            quiz.InvalidArgumentType('command', 'foobar')
        )

    def test_invalid_argument_type_optional(self):
        selection_set = _.is_housetrained(at_other_homes='foo')
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, selection_set)
        assert exc.value == quiz.SelectionError(
            Dog,
            'is_housetrained',
            quiz.InvalidArgumentType('at_other_homes', 'foo')
        )

    def test_nested_selection_error(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.owner[_.hobbies[_.foo]])
        assert exc.value == quiz.SelectionError(
            Dog,
            'owner',
            quiz.SelectionError(
                Human,
                'hobbies',
                quiz.SelectionError(
                    Hobby,
                    'foo',
                    quiz.NoSuchField()
                )
            )
        )

    def test_selection_set_on_non_object(self):
        with pytest.raises(quiz.SelectionError) as exc:
            quiz.validate(Dog, _.name[_.foo])
        assert exc.value == quiz.SelectionError(
            Dog,
            'name',
            quiz.SelectionsNotSupported()
        )

    # TODO: check object types always have selection sets

    # TODO: list input type


class TestObject:

    class TestGetItem:

        def test_valid(self):
            selection_set = (
                _
                .name
                .knows_command(command=Command.SIT)
                .is_housetrained
            )
            fragment = Dog[selection_set]
            assert fragment == quiz.InlineFragment(Dog, selection_set)

        def test_validates(self):
            with pytest.raises(quiz.SelectionError):
                Dog[_.name.foo.knows_command(command=Command.SIT)]


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
        assert isinstance(query, quiz.Operation)
        assert query.type is quiz.OperationType.QUERY  # noqa
        assert len(query.selection_set) == 1

    def test_validates(self):
        with pytest.raises(quiz.SelectionError):
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


class TestOperation:

    def test_graphql(self):
        operation = quiz.Operation(
            quiz.OperationType.QUERY,
            SelectionSet(
                quiz.Field('foo'),
                quiz.Field('qux', fdict({'buz': 99}), SelectionSet(
                    quiz.Field('nested'),
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

    def test_doc(self):
        schema = quiz.FieldSchema(
            'foo', 'my description', type=quiz.List[str],
            args=fdict.EMPTY,
            is_deprecated=False, deprecation_reason=None)
        assert '[str]' in schema.__doc__


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

        def test_argument_named_self(self):
            assert _.foo(self=4, bla=3) == SelectionSet(
                Field('foo', fdict({'self': 4, 'bla': 3})))

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


class TestRaw:

    def test_gql(self):
        raw = quiz.Raw('my raw graphql')
        assert gql(raw) == 'my raw graphql'
