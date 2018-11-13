from datetime import datetime
from textwrap import dedent

import pytest

import quiz
from quiz import SELECTOR as _
from quiz.build import SelectionSet, gql
from quiz.utils import FrozenDict as fdict

from .example import (Color, Command, Dog, DogQuery, Hobby, Human, MyDateTime,
                      SearchFilters, Sentient, Order)
from .helpers import AlwaysEquals, NeverEquals


class TestUnion:

    def test_instancecheck(self):

        class MyUnion(quiz.Union):
            __args__ = (str, int)

        assert isinstance('foo', MyUnion)
        assert isinstance(5, MyUnion)
        assert not isinstance(1.3, MyUnion)


class TestNullable:

    def test_instancecheck(self, mocker):

        class MyOptional(quiz.Nullable):
            __arg__ = int

        assert isinstance(5, MyOptional)
        assert isinstance(None, MyOptional)
        assert not isinstance(5.4, MyOptional)

        assert MyOptional == quiz.Nullable[int]
        assert MyOptional == mocker.ANY
        assert not MyOptional != mocker.ANY


class TestList:

    def test_isinstancecheck(self, mocker):

        class MyList(quiz.List):
            __arg__ = int

        assert isinstance([1, 2], MyList)
        assert isinstance([], MyList)
        assert not isinstance(['foo'], MyList)
        assert not isinstance([3, 'bla'], MyList)
        assert not isinstance((1, 2), MyList)

        assert MyList == quiz.List[int]
        assert MyList == mocker.ANY
        assert not MyList != mocker.ANY


class TestGenericScalar:

    def test_isinstancecheck(self):

        class MyScalar(quiz.GenericScalar):
            """foo"""

        assert issubclass(MyScalar, quiz.Scalar)

        assert isinstance(4, MyScalar)
        assert isinstance(u'foo', MyScalar)
        assert isinstance(0.1, MyScalar)
        assert isinstance(True, MyScalar)

        assert not isinstance([], MyScalar)
        assert not isinstance(None, MyScalar)


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

    def test_repr(self):
        d = Dog(name='rufus', foo=9)
        assert "name='rufus'" in repr(d)
        assert 'foo=9' in repr(d)
        assert repr(d).startswith('Dog(')

    def test_equality(self):
        class Foo(quiz.Object):
            pass

        class Bar(quiz.Object):
            pass

        f1 = Foo(bla=9, qux=[])
        assert f1 == Foo(bla=9, qux=[])
        assert not f1 == Foo(bla=9, qux=[], t=.1)
        assert not f1 == Bar(bla=9, qux=[])
        assert f1 == AlwaysEquals()
        assert not f1 == NeverEquals()

        assert f1 != Foo(bla=9, qux=[], t=.1)
        assert f1 != Bar(bla=9, qux=[])
        assert not f1 != Foo(bla=9, qux=[])
        assert f1 != NeverEquals()
        assert not f1 != AlwaysEquals()

    class TestInit:

        def test_simple(self):
            d = Dog(foo=4, name='Bello')
            assert d.foo == 4
            assert d.name == 'Bello'

        def test_kwarg_named_self(self):
            d = Dog(self='foo')
            d.self == 'foo'

        def test_positional_arg(self):
            with pytest.raises(TypeError, match='argument'):
                Dog('foo')

        @pytest.mark.xfail(reason='not yet implemented')
        def test_dunder(self):
            with pytest.raises(TypeError, match='underscore'):
                Dog(__foo__=9)


class TestInputObject:

    def test_init_full(self):
        search = SearchFilters(field='foo', order=Order.ASC)
        assert search.field == 'foo'
        assert search.order is Order.ASC

        with pytest.raises(AttributeError):
            search.order = 'foo'

    def test_init_partial(self):
        search = SearchFilters(field='foo')
        assert search.field == 'foo'

        with pytest.raises(quiz.NoValueForField):
            assert search.order is None

        assert not hasattr(search, 'order')

    def test_kwargs_named_self(self):

        class Foo(quiz.InputObject):
            __input_fields__ = {
                'self': quiz.InputValue(
                    'self',
                    'example field',
                    type=int,
                )
            }
            self = quiz.InputObjectFieldDescriptor(
                quiz.InputValue(
                    'self',
                    'example field',
                    type=int,
                )
            )

        foo = Foo(self=4)
        assert foo.self == 4


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


def test_selection_error_str():
    exc = quiz.SelectionError(Dog, 'best_friend.foo',
                              quiz.NoSuchArgument('bla'))
    assert str(exc).strip() == dedent('''\
    SelectionError on "Dog" at path "best_friend.foo":

        NoSuchArgument: argument "bla" does not exist''')


@pytest.mark.parametrize('name', ['foo', 'bar'])
def test_no_such_argument_str(name):
    exc = quiz.NoSuchArgument(name)
    assert str(exc) == 'argument "{}" does not exist'.format(name)


def test_no_such_field_str():
    exc = quiz.NoSuchField()
    assert str(exc) == 'field does not exist'


@pytest.mark.parametrize('name', ['foo', 'bar'])
def test_invalid_arg_type_str(name):
    exc = quiz.InvalidArgumentType(name, 5)
    assert str(exc) == (
        'invalid value "5" of type {} for argument "{}"'.format(int, name))


@pytest.mark.parametrize('name', ['foo', 'bar'])
def test_missing_argument_str(name):
    exc = quiz.MissingArgument(name)
    assert str(exc) == 'argument "{}" missing (required)'.format(name)


def test_selections_not_supported_str():
    exc = quiz.SelectionsNotSupported()
    assert str(exc) == 'selections not supported on this object'


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
            .age(on_date=MyDateTime(datetime.now()))
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


class TestLoadField:

    def test_custom_scalar(self):
        result = quiz.types.load_field(MyDateTime, quiz.Field('foo'), 12345)
        assert isinstance(result, MyDateTime)
        assert result.dtime == datetime.fromtimestamp(12345)

    @pytest.mark.parametrize('value', [
        1,
        u'a string',
        0.4,
        True,
    ])
    def test_generic_scalar(self, value):
        result = quiz.types.load_field(quiz.GenericScalar,
                                       quiz.Field('data'), value)
        assert type(result) == type(value)  # noqa
        assert result == value

    def test_namespace(self):
        field = quiz.Field('dog', selection_set=(
            _
            .name
            .color
            ('hooman').owner
        ))
        result = quiz.types.load_field(Dog, field, {
            'name': u'Fred',
            'color': u'BROWN',
            'hooman': None
        })
        assert isinstance(result, Dog)
        assert result == Dog(name=u'Fred', color=Color.BROWN, hooman=None)

    @pytest.mark.parametrize('value, expect', [
        (None, None),
        (u'BLACK', Color.BLACK),
    ])
    def test_nullable(self, value, expect):
        result = quiz.types.load_field(quiz.Nullable[Color],
                                       quiz.Field('color'), value)
        assert result is expect

    @pytest.mark.parametrize('value, expect', [
        ([], []),
        ([{'name': u'sailing'}, {'name': u'bowling'}, None],
         [Hobby(name=u'sailing'), Hobby(name=u'bowling'), None]),
    ])
    def test_list(self, value, expect):
        field = quiz.Field('foo', selection_set=_.name)
        result = quiz.types.load_field(quiz.List[quiz.Nullable[Hobby]],
                                       field, value)
        assert result == expect

    def test_enum(self):
        result = quiz.types.load_field(Color, quiz.Field('data'), 'BROWN')
        assert result is Color.BROWN

    def test_primitive_type(self):
        result = quiz.types.load_field(int, quiz.Field('age'), 4)
        assert result == 4


class TestLoad:

    def test_empty(self):
        selection = quiz.SelectionSet()
        loaded = quiz.load(DogQuery, selection, {})
        assert isinstance(loaded, DogQuery)

    def test_full(self):
        selection = (
            _
            .dog[
                _
                .name
                .color
                ('knows_sit').knows_command(command=Command.SIT)
                ('knows_roll').knows_command(command=Command.ROLL_OVER)
                .is_housetrained
                .owner[
                    _
                    .name
                    .hobbies[
                        _
                        .name
                        ('coolness').cool_factor
                    ]
                ]
                .best_friend[
                    _
                    .name
                ]
                .age(on_date=MyDateTime(datetime.now()))
                .birthday
            ]
        )
        loaded = quiz.load(DogQuery, selection, {
            'dog': {
                'name': u'Rufus',
                'color': u'GOLDEN',
                'knows_sit': True,
                'knows_roll': False,
                'is_housetrained': True,
                'owner': {
                    'name': u'Fred',
                    'hobbies': [
                        {
                            'name': u'stamp collecting',
                            'coolness': 2,
                        },
                        {
                            'name': u'snowboarding',
                            'coolness': 8,
                        }
                    ]
                },
                'best_friend': {
                    'name': u'Sally',
                },
                'age': 3,
                'birthday': 1540731645,
            }
        })
        # TODO: include union types
        assert isinstance(loaded, DogQuery)
        assert loaded == DogQuery(
            dog=Dog(
                name='Rufus',
                color=Color.GOLDEN,
                knows_sit=True,
                knows_roll=False,
                is_housetrained=True,
                owner=Human(
                    name='Fred',
                    hobbies=[
                        Hobby(name='stamp collecting', coolness=2),
                        Hobby(name='snowboarding', coolness=8)
                    ]
                ),
                best_friend=Sentient(name='Sally'),
                age=3,
                birthday=MyDateTime(datetime.fromtimestamp(1540731645)),
            )
        )

    def test_nulls(self):
        selection = (
            _
            .dog[
                _
                .name
                ('knows_sit').knows_command(command=Command.SIT)
                ('knows_roll').knows_command(command=Command.ROLL_OVER)
                .is_housetrained
                .owner[
                    _
                    .name
                    .hobbies[
                        _
                        .name
                        ('coolness').cool_factor
                    ]
                ]
                .best_friend[
                    _
                    .name
                ]
                .age(on_date=MyDateTime(datetime.now()))
                .birthday
            ]
        )
        loaded = quiz.load(DogQuery, selection, {
            'dog': {
                'name': u'Rufus',
                'knows_sit': True,
                'knows_roll': False,
                'is_housetrained': True,
                'owner': None,
                'best_friend': None,
                'age': 3,
                'birthday': 1540731645,
            }
        })
        assert isinstance(loaded, DogQuery)
        assert loaded == DogQuery(
            dog=Dog(
                name='Rufus',
                knows_sit=True,
                knows_roll=False,
                is_housetrained=True,
                owner=None,
                best_friend=None,
                age=3,
                birthday=MyDateTime(datetime.fromtimestamp(1540731645)),
            )
        )


class TestFieldDefinition:

    def test_doc(self):
        schema = quiz.FieldDefinition(
            'foo', 'my description', type=quiz.List[str],
            args=fdict.EMPTY,
            is_deprecated=False, deprecation_reason=None)
        assert '[str]' in schema.__doc__

    def test_descriptor(self):

        class Foo(object):
            bla = quiz.FieldDefinition(
                'bla', 'my description',
                args=fdict.EMPTY,
                type=quiz.List[int],
                is_deprecated=False, deprecation_reason=None)

        f = Foo()

        with pytest.raises(quiz.NoValueForField) as exc:
            f.bla

        assert isinstance(exc.value, AttributeError)

        f.__dict__.update({'bla': 9, 'qux': 'foo'})

        assert f.bla == 9
        assert f.qux == 'foo'

        with pytest.raises(AttributeError, match='set'):
            f.bla = 3
