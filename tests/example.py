"""An example schema, defined in python types."""
from datetime import datetime
from functools import partial

import six

import quiz as q
from quiz.utils import FrozenDict

mkfield = partial(q.FieldDefinition,
                  args=FrozenDict.EMPTY,
                  is_deprecated=False,
                  desc='',
                  deprecation_reason=None)


Command = q.Enum('Command', {
    'SIT': 'SIT',
    'DOWN': 'DOWN',
    'ROLL_OVER': 'ROLL_OVER',
})
Color = q.Enum('Color', {
    'BROWN': 'BROWN',
    'BLACK': 'BLACK',
    'GOLDEN': 'GOLDEN',
})
Order = q.Enum('Order', {
    'ASC': 'ASC',
    'DESC': 'DESC',
})


class MyDateTime(q.Scalar):
    """an example datetime"""
    def __init__(self, dtime):
        self.dtime = dtime

    def __gql_dump__(self):
        """The datetime as a timestamp"""
        return (self.dtime - datetime(1970, 1, 1)).total_seconds()

    @classmethod
    def __gql_load__(cls, data):
        return cls(datetime.fromtimestamp(data))

    def __eq__(self, other):
        return self.dtime == other.dtime


@six.add_metaclass(q.Interface)
class Sentient(q.types.Namespace):
    name = mkfield('name', type=six.text_type)


class Hobby(q.Object):
    name = mkfield('name', type=six.text_type)
    cool_factor = mkfield('description', type=int)


class Human(Sentient, q.Object):
    name = mkfield('name', type=six.text_type)
    hobbies = mkfield('hobbies',
                      type=q.Nullable[q.List[q.Nullable[Hobby]]])


class Alien(Sentient, q.Object):
    name = mkfield('name', type=six.text_type)
    home_planet = mkfield('home_planer', type=q.Nullable[six.text_type])


class Dog(Sentient, q.Object):
    """An example type"""
    name = mkfield('name', type=six.text_type)
    color = mkfield('color', type=q.Nullable[Color])
    is_housetrained = mkfield(
        'is_housetrained',
        args=FrozenDict({
            'at_other_homes': q.InputValueDefinition(
                'at_other_homes',
                '',
                type=q.Nullable[bool]
            )
        }),
        type=bool)
    bark_volume = mkfield('bark_volume', type=int)
    knows_command = mkfield(
        'knows_command',
        args=FrozenDict({
            'command': q.InputValueDefinition(
                'command',
                'the command',
                type=Command
            ),
        }),
        type=bool
    )
    owner = mkfield('owner', type=q.Nullable[Human])
    best_friend = mkfield('best_friend', type=q.Nullable[Sentient])
    age = mkfield(
        'age',
        type=int,
        args=FrozenDict({
            'on_date': q.InputValueDefinition(
                'on_date',
                '',
                type=q.Nullable[MyDateTime]
            )
        })
    )
    birthday = mkfield('birthday', type=MyDateTime)
    data = mkfield('data', type=q.AnyScalar)


class SearchFilters(q.InputObject):
    """filters for searching"""
    __input_fields__ = {
        'field': q.InputValueDefinition(
            'field',
            'the field to filter on',
            type=str,
        ),
        'order': q.InputValueDefinition(
            'order',
            'the ordering',
            type=q.Nullable[Order],
        )
    }

    field = q.InputObjectFieldDescriptor(
        q.InputValueDefinition(
            'field',
            'the field to filter on',
            type=str,
        )
    )
    order = q.InputObjectFieldDescriptor(
        q.InputValueDefinition(
            'order',
            'the ordering',
            type=q.Nullable[Order],
        )
    )


class DogQuery(q.Object):
    dog = mkfield('dog', type=Dog)
    search_dogs = mkfield(
        'search_dogs',
        args=FrozenDict({
            'filters': q.InputValueDefinition(
                'filters',
                'the search filters',
                type=SearchFilters
            )
        }),
        type=Dog)


class Person(q.Union):
    __args__ = (Human, Alien)


Human.best_friend = mkfield('best_friend', type=q.Nullable[Person])
