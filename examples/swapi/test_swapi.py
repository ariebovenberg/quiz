from pathlib import Path
import datetime
import json

import requests
import snug

import quiz
_ = quiz.build.field_chain

__HERE = Path(__file__).parent

SCHEMA_PATH = Path(__file__).parent / 'schema.json'
URL = 'https://api.graphcms.com/simple/v1/swapi'

execute = snug.executor(client=requests.Session())

# uncomment to retrieve the lastest schema
# schema = execute(quiz.schema.get(URL))
# with SCHEMA_PATH.open('w') as rfile:
#     schema = json.dump(schema, rfile)

with SCHEMA_PATH.open() as rfile:
    schema = json.load(rfile)


SCALARS = {
    'DateTime': datetime.datetime,
}

classes = quiz.types.build(quiz.schema.load(schema), SCALARS)
sw = quiz.build.Namespace(URL, classes)

example_query = sw[
    _
    .Starship(name='Millennium Falcon')[
        _
        .name
        .hyperdriveRating
        .pilots(orderBy=sw.PersonOrderBy.height_DESC)[
            _
            .name
            .height
            .homeworld[
                _.name
            ]
        ]
    ]
]

print(example_query)

result = execute(example_query)

print(result)

breakpoint()

a = 4
