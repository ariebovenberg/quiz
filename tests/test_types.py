import enum
import typing as t
from textwrap import dedent

import pytest

import quiz
from quiz import gql, schema, types
from quiz.types import Error, Field, InlineFragment, SelectionSet
from quiz.types import selector as _
from quiz.utils import FrozenDict as fdict

from .example import Command, Dog, Hobby, Query


class TestEnumAsType:

    def test_simple(self):
        enum_schema = schema.Enum('MyValues', 'my enum!', values=[
            schema.EnumValue(
                'foo',
                'foo value...',
                True,
                'this is deprecated!'
            ),
            schema.EnumValue(
                'blabla',
                '...',
                False,
                None
            ),
            schema.EnumValue(
                'qux',
                'qux value.',
                False,
                None
            )
        ])
        created = types.enum_as_type(enum_schema)
        assert issubclass(created, types.Enum)
        assert issubclass(created, enum.Enum)

        assert created.__name__ == 'MyValues'
        assert created.__doc__ == 'my enum!'

        assert len(created.__members__) == 3

        for (name, member), member_schema in zip(
                created.__members__.items(), enum_schema.values):
            assert name == member_schema.name
            assert member.name == name
            assert member.value == name
            assert member.__doc__ == member_schema.desc

    def test_empty(self):
        created = types.enum_as_type(schema.Enum('MyValues', '', values=[]))
        assert issubclass(created, types.Enum)
        assert issubclass(created, enum.Enum)
        assert len(created.__members__) == 0


class TestUnionAsType:

    def test_simple(self):
        union_schema = schema.Union('Foo', 'my union!', [
            schema.TypeRef('BlaType', schema.Kind.OBJECT, None),
            schema.TypeRef('Quxlike', schema.Kind.INTERFACE, None),
            schema.TypeRef('Foobar', schema.Kind.UNION, None),
        ])

        objs = {
            'BlaType': type('BlaType', (), {}),
            'Quxlike': type('Quxlike', (), {}),
            'Foobar': type('Foobar', (), {}),
            'Bla': type('Bla', (), {}),
        }

        created = types.union_as_type(union_schema, objs)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'my union!'
        assert created.__origin__ == t.Union

        assert created.__args__ == (
            objs['BlaType'],
            objs['Quxlike'],
            objs['Foobar'],
        )


class TestInterfaceAsType:

    def test_simple(self):
        interface_schema = schema.Interface('Foo', 'my interface!', [
            schema.Field(
                'blabla',
                type=schema.TypeRef('String', schema.Kind.SCALAR, None),
                args=[],
                desc='my description',
                is_deprecated=False,
                deprecation_reason=None,
            ),
        ])
        created = types.interface_as_type(interface_schema)

        assert issubclass(created, types.Interface)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'my interface!'


class TestObjectAsType:

    def test_simple(self):
        obj_schema = schema.Object(
            'Foo',
            'the foo description!',
            interfaces=[
                schema.TypeRef('Interface1', schema.Kind.INTERFACE, None),
                schema.TypeRef('BlaInterface', schema.Kind.INTERFACE, None),
            ],
            input_fields=None,
            fields=[
                schema.Field(
                    'blabla',
                    type=schema.TypeRef('String', schema.Kind.SCALAR, None),
                    args=[],
                    desc='my description',
                    is_deprecated=False,
                    deprecation_reason=None,
                ),
            ]
        )
        interfaces = {
            'Interface1': type('Interface1', (types.Interface, ), {}),
            'BlaInterface': type('BlaInterface', (types.Interface, ), {}),
            'Qux': type('Qux', (types.Interface, ), {}),
        }
        created = types.object_as_type(obj_schema, interfaces)
        assert issubclass(created, types.Object)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'the foo description!'
        assert issubclass(created, interfaces['Interface1'])
        assert issubclass(created, interfaces['BlaInterface'])

    # TODO: test without interfaces


class TestResolveTypeRef:

    def test_default(self):
        ref = schema.TypeRef('Foo', schema.Kind.ENUM, None)

        classes = {'Foo': types.Enum('Foo', {})}
        resolved = types.resolve_typeref(ref, classes)
        assert resolved == t.Optional[classes['Foo']]

    def test_non_null(self):
        ref = schema.TypeRef(None, schema.Kind.NON_NULL,
                             schema.TypeRef('Foo', schema.Kind.OBJECT, None))

        classes = {'Foo': type('Foo', (), {})}
        resolved = types.resolve_typeref(ref, classes)
        assert resolved == classes['Foo']

    def test_list(self):
        ref = schema.TypeRef(None, schema.Kind.LIST,
                             schema.TypeRef('Foo', schema.Kind.OBJECT, None))
        classes = {'Foo': type('Foo', (), {})}
        resolved = types.resolve_typeref(ref, classes)
        assert resolved == t.Optional[t.List[t.Optional[classes['Foo']]]]

    def test_list_non_null(self):
        ref = schema.TypeRef(
            None, schema.Kind.NON_NULL,
            schema.TypeRef(
                None, schema.Kind.LIST,
                schema.TypeRef(
                    None, schema.Kind.NON_NULL,
                    schema.TypeRef('Foo', schema.Kind.OBJECT, None)
                )))
        classes = {'Foo': type('Foo', (), {})}
        resolved = types.resolve_typeref(ref, classes)
        assert resolved == t.List[classes['Foo']]


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


class TestField:

    # TODO: add tests for __eq__

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
