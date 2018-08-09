import datetime
import json
from pathlib import Path

import requests
import snug

import quiz

_ = quiz.types.selector

# NAME = 'test_github.my_types'
URL = "https://api.github.com/graphql"

SCHEMA_PATH = Path(__file__).parent / 'schema.json'

# uncomment to retrieve the lastest schema
# schema = execute(quiz.schema.get(URL))
# with SCHEMA_PATH.open('w') as rfile:
#     schema = json.dump(schema, rfile)

with SCHEMA_PATH.open('rt') as rfile:
    schema = json.load(rfile)

TOKEN = Path('~/.snug/github_token.txt').expanduser().read_text().strip()


def bearer_auth(req):
    return req.with_headers({
        'Authorization': f'bearer {TOKEN}'
    })


URI = type('URI', (str, ), {})
HTML = type('HTML', (str, ), {})
GitObjectID = type('GitObjectID', (str, ), {})
GitTimestamp = type('GitTimestamp', (str, ), {})
X509Certificate = type('X509Certificate', (str, ), {})
GitSSHRemote = type('GitSSHRemote', (str, ), {})


SCALARS = {
    'URI':             URI,
    'DateTime':        datetime.datetime,
    'HTML':            HTML,
    'GitObjectID':     GitObjectID,
    'GitTimestamp':    GitTimestamp,
    'Date':            datetime.date,
    'X509Certificate': X509Certificate,
    'GitSSHRemote':    GitSSHRemote,
}


classes = quiz.types.gen(quiz.schema.load(schema), SCALARS)
gh = quiz.types.Namespace(URL, classes)

execute = snug.executor(auth=bearer_auth, client=requests.Session())

example_query = gh.query(
    _
    .rateLimit[
        _
        .remaining
        .resetAt
    ]
    .repository(owner='octocat', name='hello-world')[
        _
        .createdAt
    ]
    .organization(login='github')[
        _
        .location
        .members(first=10)[
            _.edges[
                _.node[
                    _.id
                ]
            ]
        ]
    ]
    # TODO: support raw graphql
    # .organization(login='github')['''
    #   location
    #   members(first: 10) {
    #     edges {
    #       node {
    #         id
    #       }
    #     }
    #   }
    # ''']
)

print(example_query)

breakpoint()
result = execute(example_query)

# example_mutation = gh.mutation

print(result)

breakpoint()
