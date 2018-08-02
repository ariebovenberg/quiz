import typing as t
import enum

from quiz import schema, types


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
