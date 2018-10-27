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


def pytest_addoption(parser):
    parser.addoption(
        "--live", action="store_true", default=False, help="run live tests"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        # --live given in cli: do not skip live tests
        return
    skip_live = pytest.mark.skip(reason="need --live option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_live)
