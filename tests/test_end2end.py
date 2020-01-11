import os
from dataclasses import dataclass
from datetime import datetime

import pytest
import quiz
from quiz import _

GITHUB_USER = os.environ.get("QUIZ_GITHUB_USER")
GITHUB_TOKEN = os.environ.get("QUIZ_GITHUB_TOKEN")


DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class DateTime(quiz.Scalar):
    inner: datetime

    @classmethod
    def coerce(cls, value: object) -> "DateTime":
        if isinstance(value, datetime):
            return cls(value)
        else:
            raise quiz.CouldNotCoerce(
                "{!r} is not a valid datetime".format(value)
            )

    def __gql_dump__(self) -> str:
        return self.inner.strftime(DATETIME_FORMAT)

    @classmethod
    def __gql_load__(self, data: str) -> datetime:
        return datetime.strptime(data, DATETIME_FORMAT)


@pytest.mark.live
@pytest.mark.skipif(
    not (GITHUB_USER and GITHUB_TOKEN),
    reason="Missing github credential environment variables",
)
def test_end2end(raw_schema):
    schema = quiz.Schema.from_raw(raw_schema, scalars=[DateTime])

    # TODO: inline fragments (on pull request?)

    # fmt: off
    issues_selection = (
        _
        .pageInfo[
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
            .labels(first=100)[
                _
                .edges[
                    _
                    .node[
                        _
                        .name
                    ]
                ]
            ]
        ]
    )

    query = schema.query[
        _
        .repository(owner="ariebovenberg", name="quiz")[
            _
            .issues(
                first=30,
                filterBy=schema.IssueFilters(
                    since=datetime(2018, 1, 1),
                    states=['OPEN', schema.IssueState.CLOSED]
                )
            )[
                issues_selection
            ]
            ('unassigned_issues').issues(
                first=3,
                # dict coercion to input value
                filterBy={'assignee': None}
            )[
                issues_selection
            ]
        ]
    ]
    # fmt: on
    result = quiz.execute(
        query,
        url="https://api.github.com/graphql",
        auth=(GITHUB_USER, GITHUB_TOKEN),
    )
    first_issue = result.repository.issues.nodes[0]
    assert first_issue.title == "Does it support headers?"
    assert first_issue.createdAt == datetime(2018, 9, 13, 9, 18, 13)
