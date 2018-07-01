import datetime
import json
from pathlib import Path

import requests
import snug

import quiz

_ = quiz.F

NAME = 'test_github.my_types'

SCHEMA_PATH = Path(__file__).parent / 'schema.json'
with SCHEMA_PATH.open('rt') as rfile:
    schema = json.load(rfile)

TOKEN = Path('~/.snug/github_token.txt').expanduser().read_text().strip()


def bearer_auth(req):
    return req.with_headers({
        'Authorization': f'bearer {TOKEN}'
    })


ID = type('ID', (str, ), {})
URI = type('URI', (str, ), {})
HTML = type('HTML', (str, ), {})
GitObjectID = type('GitObjectID', (str, ), {})
GitTimestamp = type('GitTimestamp', (str, ), {})
X509Certificate = type('X509Certificate', (str, ), {})
GitSSHRemote = type('GitSSHRemote', (str, ), {})


SCALARS = {
    'Boolean':         bool,
    'String':          str,
    'ID':              ID,
    'URI':             URI,
    'Int':             int,
    'DateTime':        datetime.datetime,
    'HTML':            HTML,
    'GitObjectID':     GitObjectID,
    'GitTimestamp':    GitTimestamp,
    'Float':           float,
    'Date':            datetime.date,
    'X509Certificate': X509Certificate,
    'GitSSHRemote':    GitSSHRemote,
}


classes = list(quiz.make_classes(schema, SCALARS))
gh = quiz.make_namespace(classes)
# sys.modules[NAME] = quiz.make_module(NAME, classes)

execute = snug.executor(auth=bearer_auth, client=requests.Session())

q = gh.query[
    _.rateLimit[
        _.remaining
        .nodeCount
    ]
]

print(quiz.gql(q))

result = execute(q)

print(result)

breakpoint()
