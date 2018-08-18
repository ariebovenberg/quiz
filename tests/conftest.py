import pytest


@pytest.fixture(scope='session')
def event_loop():
    import asyncio
    return asyncio.get_event_loop()
