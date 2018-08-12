import json
from pathlib import Path

import pytest

import quiz


@pytest.fixture(scope='session')
def raw_schema():
    with (Path(__file__).parent / 'example_schema.json').open() as rfile:
        return json.load(rfile)


@pytest.fixture(scope='session')
def type_schemas(raw_schema):
    return list(quiz.schema.load(raw_schema))
