import json
from pathlib import Path

import quiz

with (Path(__file__).parent / 'example_schema.json').open() as rfile:
    SCHEMA = json.load(rfile)


# TODO: expand tests
def test_load():
    loaded = list(quiz.schema.load(SCHEMA))
    assert loaded
