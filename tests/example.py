import typing as t
from functools import partial

from quiz import types
from quiz.utils import FrozenDict

mkfield = partial(types.FieldSchema,
                  args=FrozenDict.EMPTY,
                  is_deprecated=False,
                  desc='',
                  deprecation_reason=None)


Command = types.Enum('Command', {'SIT': 'SIT', 'DOWN': 'DOWN'})


class Sentient(types.Interface):
    name = mkfield('name', type=str)


class Hobby(types.Object):
    name = mkfield('name', type=str)
    cool_factor = mkfield('description', type=int)


class Human(Sentient, types.Object):
    name = mkfield('name', type=str)
    hobbies = mkfield('hobbies', type=t.Optional[t.List[t.Optional[Hobby]]])


class Alien(Sentient, types.Object):
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
