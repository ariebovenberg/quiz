import datetime
import enum
import typing as t

import pytest

import quiz
from quiz.schema import raw, to_types

# TODO: test help() output with pydoc.render_doc()


class TestEnumAsType:

    def test_simple(self):
        enum_schema = raw.Enum('MyValues', 'my enum!', values=[
            raw.EnumValue(
                'foo',
                'foo value...',
                True,
                'this is deprecated!'
            ),
            raw.EnumValue(
                'blabla',
                '...',
                False,
                None
            ),
            raw.EnumValue(
                'qux',
                'qux value.',
                False,
                None
            )
        ])
        created = to_types.enum_as_type(enum_schema, module_name='foo')
        assert issubclass(created, quiz.Enum)
        assert issubclass(created, enum.Enum)

        assert created.__name__ == 'MyValues'
        assert created.__doc__ == 'my enum!'
        assert created.__module__ == 'foo'

        assert len(created.__members__) == 3

        for (name, member), member_schema in zip(
                created.__members__.items(), enum_schema.values):
            assert name == member_schema.name
            assert member.name == name
            assert member.value == name
            assert member.__doc__ == member_schema.desc

    def test_empty(self):
        created = to_types.enum_as_type(raw.Enum('MyValues', '', values=[]),
                                        module_name='foo')
        assert issubclass(created, quiz.Enum)
        assert issubclass(created, enum.Enum)
        assert len(created.__members__) == 0


class TestUnionAsType:

    def test_simple(self):
        union_schema = raw.Union('Foo', 'my union!', [
            raw.TypeRef('BlaType', raw.Kind.OBJECT, None),
            raw.TypeRef('Quxlike', raw.Kind.INTERFACE, None),
            raw.TypeRef('Foobar', raw.Kind.UNION, None),
        ])

        objs = {
            'BlaType': type('BlaType', (), {}),
            'Quxlike': type('Quxlike', (), {}),
            'Foobar': type('Foobar', (), {}),
            'Bla': type('Bla', (), {}),
        }

        created = to_types.union_as_type(union_schema, objs)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'my union!'
        assert issubclass(created, quiz.Union)

        assert created.__args__ == (
            objs['BlaType'],
            objs['Quxlike'],
            objs['Foobar'],
        )


class TestInterfaceAsType:

    def test_simple(self):
        interface_schema = raw.Interface('Foo', 'my interface!', [
            raw.Field(
                'blabla',
                type=raw.TypeRef('String', raw.Kind.SCALAR, None),
                args=[],
                desc='my description',
                is_deprecated=False,
                deprecation_reason=None,
            ),
        ])
        created = to_types.interface_as_type(interface_schema,
                                             module_name='mymodule')

        assert issubclass(created, quiz.Interface)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'my interface!'
        assert created.__module__ == 'mymodule'


class TestObjectAsType:

    def test_simple(self):
        obj_schema = raw.Object(
            'Foo',
            'the foo description!',
            interfaces=[
                raw.TypeRef('Interface1', raw.Kind.INTERFACE, None),
                raw.TypeRef('BlaInterface', raw.Kind.INTERFACE, None),
            ],
            input_fields=None,
            fields=[
                raw.Field(
                    'blabla',
                    type=raw.TypeRef('String', raw.Kind.SCALAR, None),
                    args=[],
                    desc='my description',
                    is_deprecated=False,
                    deprecation_reason=None,
                ),
            ]
        )
        interfaces = {
            'Interface1': type('Interface1', (quiz.Interface, ), {}),
            'BlaInterface': type('BlaInterface', (quiz.Interface, ), {}),
            'Qux': type('Qux', (quiz.Interface, ), {}),
        }
        created = to_types.object_as_type(obj_schema, interfaces,
                                          module_name='foo')
        assert issubclass(created, quiz.Object)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'the foo description!'
        assert created.__module__ == 'foo'
        assert issubclass(created, interfaces['Interface1'])
        assert issubclass(created, interfaces['BlaInterface'])

    # TODO: test without interfaces


class TestResolveTypeRef:

    def test_default(self):
        ref = raw.TypeRef('Foo', raw.Kind.ENUM, None)

        classes = {'Foo': quiz.Enum('Foo', {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert resolved == t.Optional[classes['Foo']]

    def test_non_null(self):
        ref = raw.TypeRef(None, raw.Kind.NON_NULL,
                          raw.TypeRef('Foo', raw.Kind.OBJECT, None))

        classes = {'Foo': type('Foo', (), {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert resolved == classes['Foo']

    def test_list(self):
        ref = raw.TypeRef(None, raw.Kind.LIST,
                          raw.TypeRef('Foo', raw.Kind.OBJECT, None))
        classes = {'Foo': type('Foo', (), {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert resolved == t.Optional[t.List[t.Optional[classes['Foo']]]]

    def test_list_non_null(self):
        ref = raw.TypeRef(
            None, raw.Kind.NON_NULL,
            raw.TypeRef(
                None, raw.Kind.LIST,
                raw.TypeRef(
                    None, raw.Kind.NON_NULL,
                    raw.TypeRef('Foo', raw.Kind.OBJECT, None)
                )))
        classes = {'Foo': type('Foo', (), {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert resolved == t.List[classes['Foo']]


class TestBuild:

    def test_missing_scalars(self, type_schemas):
        with pytest.raises(Exception, match='DateTime'):
            quiz.schema.build(type_schemas, scalars={}, module_name='foo')

    def test_valid(self, type_schemas):
        classes = quiz.schema.build(type_schemas, scalars={
            'URI':             str,
            'DateTime':        datetime.datetime,
            'HTML':            str,
            'GitObjectID':     str,
            'GitTimestamp':    str,
            'Date':            datetime.date,
            'X509Certificate': str,
            'GitSSHRemote':    str,
        }, module_name='mymodule')
        assert issubclass(classes['Query'], quiz.Object)
