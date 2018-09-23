import json
import sys

import pytest
import six
import snug

import quiz

from .example import Dog, DogQuery
from .helpers import MockClient

_ = quiz.SELECTOR

py3 = pytest.mark.skipif(sys.version_info < (3, ), reason='python 3+ only')


if six.PY3:
    import asyncio
    snug.send_async.register(MockClient, asyncio.coroutine(MockClient.send))


def token_auth(token):
    return snug.header_adder({'Authorization': 'token {}'.format(token)})


class TestExecute:

    def test_simple_string(self):
        client = MockClient(snug.Response(200, b'{"data": {"foo": 4}}'))
        result = quiz.execute('my query', url='https://my.url/api',
                              client=client, auth=token_auth('foo'))
        assert result == {'foo': 4}

        request = client.request
        assert request.url == 'https://my.url/api'
        assert request.method == 'POST'
        assert json.loads(request.content.decode()) == {'query': 'my query'}
        assert request.headers == {'Authorization': 'token foo',
                                   'Content-Type': 'application/json'}

    def test_query(self):
        query = quiz.Query(
            DogQuery,
            _
            .dog[
                _
                .name
                .bark_volume
            ]
        )
        client = MockClient(snug.Response(200, json.dumps({
            'data': {
                'dog': {
                    'name': 'Fred',
                    'bark_volume': 8,
                }
            }
        }).encode()))
        result = quiz.execute(query, url='https://my.url/api', client=client)
        assert result == DogQuery(
            dog=Dog(
                name='Fred',
                bark_volume=8,
            )
        )

        request = client.request
        assert request.url == 'https://my.url/api'
        assert request.method == 'POST'
        assert json.loads(request.content.decode()) == {
            'query': quiz.gql(query)}
        assert request.headers == {'Content-Type': 'application/json'}

    def test_errors(self):
        client = MockClient(snug.Response(200, json.dumps({
            'data': {'foo': 4},
            'errors': [{'message': 'foo'}]
        }).encode()))
        with pytest.raises(quiz.ErrorResponse) as exc:
            quiz.execute('my query', url='https://my.url/api',
                         client=client, auth=token_auth('foo'))
        assert exc.value == quiz.ErrorResponse({'foo': 4},
                                               [{'message': 'foo'}])


def test_executor():
    executor = quiz.executor(url='https://my.url/graphql')
    assert executor.func is quiz.execute
    assert executor.keywords['url'] == 'https://my.url/graphql'


@py3
class TestExecuteAsync:

    def test_success(self, event_loop):
        client = MockClient(snug.Response(200, b'{"data": {"foo": 4}}'))
        future = quiz.execute_async('my query', url='https://my.url/api',
                                    auth=token_auth('foo'), client=client)
        result = event_loop.run_until_complete(future)
        assert result == {'foo': 4}

        request = client.request
        assert request.url == 'https://my.url/api'
        assert request.method == 'POST'
        assert json.loads(request.content.decode()) == {'query': 'my query'}
        assert request.headers == {'Authorization': 'token foo',
                                   'Content-Type': 'application/json'}

    def test_non_string(self, event_loop):
        query = quiz.Query(
            DogQuery,
            _
            .dog[
                _
                .name
                .bark_volume
            ]
        )
        client = MockClient(snug.Response(200, json.dumps({
            'data': {
                'dog': {
                    'name': 'Fred',
                    'bark_volume': 8,
                }
            }
        }).encode()))

        future = quiz.execute_async(query,
                                    url='https://my.url/api', client=client)
        result = event_loop.run_until_complete(future)
        assert result == DogQuery(
            dog=Dog(
                name='Fred',
                bark_volume=8,
            )
        )

        request = client.request
        assert request.url == 'https://my.url/api'
        assert request.method == 'POST'
        assert json.loads(request.content.decode()) == {
            'query': quiz.gql(query)}
        assert request.headers == {'Content-Type': 'application/json'}

    def test_errors(self, event_loop):
        client = MockClient(snug.Response(200, json.dumps({
            'data': {'foo': 4},
            'errors': [{'message': 'foo'}]
        }).encode()))
        future = quiz.execute_async('my query', url='https://my.url/api',
                                    client=client, auth=token_auth('foo'))
        with pytest.raises(quiz.ErrorResponse) as exc:
            event_loop.run_until_complete(future)

        assert exc.value == quiz.ErrorResponse({'foo': 4},
                                               [{'message': 'foo'}])


@py3
def test_async_executor():
    executor = quiz.async_executor(url='https://my.url/graphql')
    assert executor.func is quiz.execute_async
    assert executor.keywords['url'] == 'https://my.url/graphql'
