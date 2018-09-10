import json
from os.path import dirname, join

import pytest


@pytest.fixture(scope='session')
def event_loop():
    import asyncio
    return asyncio.get_event_loop()


@pytest.fixture(scope='session')
def raw_schema():
    with open(join(dirname(__file__), 'example_schema.json')) as rfile:
        return json.load(rfile)
