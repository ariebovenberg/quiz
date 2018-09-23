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


class MyDateTime(q.GenericScalar):
    """a datatime string"""


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
    is_housetrained = mkfield(
        'is_housetrained',
        args=FrozenDict({
            'at_other_homes': q.InputValue(
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
            'command': q.InputValue(
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
            'on_date': q.InputValue(
                'on_date',
                '',
                type=q.Nullable[MyDateTime]
            )
        })
    )
    birthday = mkfield('birthday', type=MyDateTime)


class DogQuery(q.Object):
    dog = mkfield('dog', type=Dog)


class Person(q.Union):
    __args__ = (Human, Alien)


Human.best_friend = mkfield('best_friend', type=q.Nullable[Person])
