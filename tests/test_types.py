import enum
import typing as t
from functools import partial
from textwrap import dedent

import pytest

from quiz import schema, types
from quiz.types import selector as _, Field, InlineFragment
from quiz.utils import FrozenDict

mkfield = partial(types.FieldSchema,
                  args=FrozenDict(),
                  is_deprecated=False,
                  desc='',
                  deprecation_reason=None)


# TODO: move example schema to separate file?
Command = types.Enum('Command', {'SIT': 'SIT', 'DOWN': 'DOWN'})


class Sentient(types.Interface):
    name = mkfield('name', type=str)


class Hobby(types.Object):
    name = mkfield('name', type=str)
    cool_factor = mkfield('description', type=int)


class Human(Sentient, types.Object):
    name = mkfield('name', type=str)
    hobbies = mkfield('hobbies', type=t.Optional[t.List[t.Optional[Hobby]]])


class Alien (Sentient, types.Object):
    name = mkfield('name', type=str)
    home_planet = mkfield('home_planer', type=t.Optional[str])


class Dog(Sentient, types.Object):
    """An example type"""
    name = mkfield('name', type=str)
    is_housetrained = mkfield(
        'is_housetrained',
        args=FrozenDict({
            'at_other_homes': types.InputValue(
                'at_other_homes',
                '',
                type=t.Optional[bool]
            )
        }),
        type=bool)
    bark_volume = mkfield('bark_volume', type=int)
    knows_command = mkfield(
        'knows_command',
        args=FrozenDict({
            'command': types.InputValue(
                'command',
                'the command',
                type=Command
            ),
        }),
        type=bool
    )
    owner = mkfield('owner', type=t.Optional[Human])
    best_friend = mkfield('best_friend', type=t.Optional[Sentient])


class Query(types.Object):
    dog = mkfield('dog', type=Dog)


HumanOrAlien = t.Union[Human, Alien]

Human.best_friend = mkfield('best_friend', type=t.Optional[HumanOrAlien])


CLASSES = {
    'Dog': Dog,
    'Query': Query,
    'Command': Command,
    'Human': Human,
}


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
        assert created.__schema__ == enum_schema

        assert len(created.__members__) == 3

        for (name, member), member_schema in zip(
                created.__members__.items(), enum_schema.values):
            assert name == member_schema.name
            assert member.name == name
            assert member.value == name
            assert member.__schema__ == member_schema
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
        assert created.__schema__ == union_schema

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
        assert created.__schema__ == interface_schema


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
        assert created.__schema__ == obj_schema
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
        assert fragment.graphql() == dedent('''\
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


class TestFieldGraphQL:

    def test_empty(self):
        assert Field('foo').graphql() == 'foo'

    def test_arguments(self):
        field = Field('foo', {
            'foo': 4,
            'blabla': 'my string!',
        })

        # arguments are unordered, multiple valid options
        assert field.graphql() in [
            'foo(foo: 4, blabla: "my string!")',
            'foo(blabla: "my string!", foo: 4)',
        ]

    def test_selection_set(self):
        field = Field('bla', {'q': 9}, selection_set=(
            Field('blabla'),
            Field('foobar', {'qux': 'another string'}),
            Field('other', selection_set=(
                Field('baz'),
            )),
            InlineFragment(
                on=Dog,
                selection_set=(
                    Field('name'),
                    Field('bark_volume'),
                    Field('owner', selection_set=(
                        Field('name'),
                    ))
                )
            ),
        ))
        assert field.graphql() == dedent('''
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


class TestNamespace:

    def test_init(self):
        namespace = types.Namespace('my/url', CLASSES)
        assert namespace.url == 'my/url'
        assert namespace.classes == CLASSES
        assert namespace.Dog is Dog

    def test_query(self):
        ns = types.Namespace('my/url', CLASSES)
        query = ns.query(
            _
            .dog[
                _
                .name
                .is_housetrained
            ]
        )
        assert isinstance(query, types.Operation)
        assert query.type is types.OperationType.QUERY  # noqa
        assert len(query.selection_set) == 1

    def test_validation(self):
        ns = types.Namespace('my/url', CLASSES)
        with pytest.raises(types.NoSuchField) as exc:
            ns.query(
                _
                .dog[
                    _
                    .name
                    .is_housetrained
                    .foobar
                ]
            )
        assert exc.value == types.NoSuchField(Dog, 'foobar')


class TestOperation:

    def test_graphql(self):
        operation = types.Operation(
            types.OperationType.QUERY,
            (
                types.Field('foo'),
                types.Field('qux', {'buz': 99}, (
                    types.Field('nested'),
                ))
            )
        )
        assert operation.graphql() == dedent('''
        query {
          foo
          qux(buz: 99) {
            nested
          }
        }
        ''').strip()
