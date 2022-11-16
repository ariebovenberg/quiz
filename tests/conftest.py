import json
from os.path import dirname, join

import pytest


@pytest.fixture(scope="session")
def raw_schema():
    with open(join(dirname(__file__), "example_schema.json")) as rfile:
        return json.load(rfile)


def pytest_addoption(parser):
    parser.addoption(
        "--live", action="store_true", default=False, help="run live tests"
    )


def pytest_collection_modifyitems(config, items):  # pragma: no cover
    if config.getoption("--live"):
        # --live given in cli: do not skip live tests
        return
    skip_live = pytest.mark.skip(reason="need --live option to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
