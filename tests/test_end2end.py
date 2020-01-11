import os

import pytest
import quiz
from quiz import _

GITHUB_USER = os.environ.get("QUIZ_GITHUB_USER")
GITHUB_TOKEN = os.environ.get("QUIZ_GITHUB_TOKEN")


@pytest.mark.live
@pytest.mark.skipif(
    not (GITHUB_USER and GITHUB_TOKEN),
    reason="Missing github credential environment variables",
)
def test_end2end(raw_schema):
    schema = quiz.Schema.from_raw(raw_schema)

    # fmt: off
    query = schema.query[
        _
        .repository(owner="ariebovenberg", name="quiz")[
            _
            .issues(first=30, states=[schema.IssueState.OPEN, schema.IssueState.CLOSED])[
                _
                .pageInfo [
                    _
                    .endCursor
                ]
                .nodes[
                    _
                    .title
                    .number
                    .state
                    .closed
                    .closedAt
                    .createdAt
                    .labels(first=100) [
                        _
                        .edges [
                            _
                            .node [
                                _
                                .name
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ]
    # fmt: on
    result = quiz.execute(
        query,
        url="https://api.github.com/graphql",
        auth=(GITHUB_USER, GITHUB_TOKEN),
    )
    import pdb

    pdb.set_trace()
