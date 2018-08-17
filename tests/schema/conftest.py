import json
from os.path import dirname, join

import pytest

import quiz


@pytest.fixture(scope='session')
def raw_schema():
    with open(join(dirname(__file__), 'example_schema.json')) as rfile:
        return json.load(rfile)


@pytest.fixture(scope='session')
def type_schemas(raw_schema):
    return list(quiz.schema.load(raw_schema))
