import datetime
import enum
import json
import pydoc
from textwrap import dedent

import pytest
import six
import snug

import quiz
from quiz.schema import raw, to_types


def trim_whitespace(txt):
    return ''.join(t.rstrip() + '\n' for t in txt.splitlines())


if six.PY3:
    def render_doc(obj):
        return trim_whitespace(pydoc.render_doc(obj, renderer=pydoc.plaintext))
else:
    def render_doc(obj):
        return trim_whitespace(pydoc.plain(pydoc.render_doc(obj)))


EXAMPLE_SCALARS = {
    'URI':             str,
    'DateTime':        datetime.datetime,
    'HTML':            str,
    'GitObjectID':     str,
    'GitTimestamp':    str,
    'Date':            datetime.date,
    'X509Certificate': str,
    'GitSSHRemote':    str,
}


class TestEnumAsType:

    def test_simple(self):
        enum_schema = raw.Enum('MyValues', 'my enum!', values=[
            raw.EnumValue(
                'foo',
                'foo value...',
                True,
                'this is deprecated!'
            ),
            raw.EnumValue(
                'blabla',
                '...',
                False,
                None
            ),
            raw.EnumValue(
                'qux',
                'qux value.',
                False,
                None
            )
        ])
        created = to_types.enum_as_type(enum_schema, module_name='foo')
        assert issubclass(created, quiz.Enum)
        assert issubclass(created, enum.Enum)

        assert created.__name__ == 'MyValues'
        assert created.__doc__ == 'my enum!'
        assert created.__module__ == 'foo'

        assert len(created.__members__) == 3

        for (name, member), member_schema in zip(
                created.__members__.items(), enum_schema.values):
            assert name == member_schema.name
            assert member.name == name
            assert member.value == name
            assert member.__doc__ == member_schema.desc


class TestUnionAsType:

    def test_simple(self):
        union_schema = raw.Union('Foo', 'my union!', [
            raw.TypeRef('BlaType', raw.Kind.OBJECT, None),
            raw.TypeRef('Quxlike', raw.Kind.INTERFACE, None),
            raw.TypeRef('Foobar', raw.Kind.UNION, None),
        ])

        objs = {
            'BlaType': type('BlaType', (), {}),
            'Quxlike': type('Quxlike', (), {}),
            'Foobar': type('Foobar', (), {}),
            'Bla': type('Bla', (), {}),
        }

        created = to_types.union_as_type(union_schema, objs)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'my union!'
        assert issubclass(created, quiz.Union)

        assert created.__args__ == (
            objs['BlaType'],
            objs['Quxlike'],
            objs['Foobar'],
        )


class TestInterfaceAsType:

    def test_simple(self):
        interface_schema = raw.Interface('Foo', 'my interface!', [
            raw.Field(
                'blabla',
                type=raw.TypeRef('String', raw.Kind.SCALAR, None),
                args=[],
                desc='my description',
                is_deprecated=False,
                deprecation_reason=None,
            ),
        ])
        created = to_types.interface_as_type(interface_schema,
                                             module_name='mymodule')

        assert issubclass(created, quiz.Interface)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'my interface!'
        assert created.__module__ == 'mymodule'


class TestObjectAsType:

    def test_simple(self):
        obj_schema = raw.Object(
            'Foo',
            'the foo description!',
            interfaces=[
                raw.TypeRef('Interface1', raw.Kind.INTERFACE, None),
                raw.TypeRef('BlaInterface', raw.Kind.INTERFACE, None),
            ],
            input_fields=None,
            fields=[
                raw.Field(
                    'blabla',
                    type=raw.TypeRef('String', raw.Kind.SCALAR, None),
                    args=[],
                    desc='my description',
                    is_deprecated=False,
                    deprecation_reason=None,
                ),
            ]
        )
        interfaces = {
            'Interface1': type('Interface1', (quiz.Interface, ), {
                '__module__': 'foo'}),
            'BlaInterface': type('BlaInterface', (quiz.Interface, ), {
                '__module__': 'foo'}),
            'Qux': type('Qux', (quiz.Interface, ), {
                '__module__': 'foo'}),
        }
        created = to_types.object_as_type(obj_schema, interfaces,
                                          module_name='foo')
        assert issubclass(created, quiz.Object)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'the foo description!'
        assert created.__module__ == 'foo'
        assert issubclass(created, interfaces['Interface1'])
        assert issubclass(created, interfaces['BlaInterface'])


class TestResolveTypeRef:

    def test_default(self):
        ref = raw.TypeRef('Foo', raw.Kind.ENUM, None)

        classes = {'Foo': quiz.Enum('Foo', {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.Nullable)
        assert resolved.__arg__ is classes['Foo']

    def test_non_null(self):
        ref = raw.TypeRef(None, raw.Kind.NON_NULL,
                          raw.TypeRef('Foo', raw.Kind.OBJECT, None))

        classes = {'Foo': type('Foo', (), {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert resolved == classes['Foo']

    def test_list(self):
        ref = raw.TypeRef(None, raw.Kind.LIST,
                          raw.TypeRef('Foo', raw.Kind.OBJECT, None))
        classes = {'Foo': type('Foo', (), {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.Nullable)
        assert issubclass(resolved.__arg__, quiz.List)
        assert issubclass(resolved.__arg__.__arg__, quiz.Nullable)
        assert resolved.__arg__.__arg__.__arg__ == classes['Foo']

    def test_list_non_null(self):
        ref = raw.TypeRef(
            None, raw.Kind.NON_NULL,
            raw.TypeRef(
                None, raw.Kind.LIST,
                raw.TypeRef(
                    None, raw.Kind.NON_NULL,
                    raw.TypeRef('Foo', raw.Kind.OBJECT, None)
                )))
        classes = {'Foo': type('Foo', (), {})}
        resolved = to_types.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.List)
        assert resolved.__arg__ == classes['Foo']


class TestBuild:

    def test_missing_scalars(self, type_schemas):
        with pytest.raises(Exception, match='DateTime'):
            quiz.schema.build(type_schemas, scalars={}, module_name='foo')

    def test_valid(self, type_schemas):
        classes = quiz.schema.build(type_schemas, scalars={
            'URI':             str,
            'DateTime':        datetime.datetime,
            'HTML':            str,
            'GitObjectID':     str,
            'GitTimestamp':    str,
            'Date':            datetime.date,
            'X509Certificate': str,
            'GitSSHRemote':    str,
        }, module_name='mymodule')
        assert issubclass(classes['Query'], quiz.Object)


def test_end_to_end(type_schemas):
    classes = quiz.schema.build(type_schemas, scalars={
        'URI':             str,
        'DateTime':        datetime.datetime,
        'HTML':            str,
        'GitObjectID':     str,
        'GitTimestamp':    str,
        'Date':            datetime.date,
        'X509Certificate': str,
        'GitSSHRemote':    str,
    }, module_name='github')
    expect = dedent('''
    Python Library Documentation: class Issue

    class Issue(Node, Assignable, Closable, Comment, Updatable, \
UpdatableComment, Labelable, Lockable, Reactable, RepositoryNode, \
Subscribable, UniformResourceLocatable, quiz.core.Object)
     |  An Issue is a place to discuss ideas, enhancements, tasks, and bugs \
for a project.
     |
     |  Method resolution order:
     |      Issue
     |      Node
     |      Assignable
     |      Closable
     |      Comment
     |      Updatable
     |      UpdatableComment
     |      Labelable
     |      Lockable
     |      Reactable
     |      RepositoryNode
     |      Subscribable
     |      UniformResourceLocatable
     |      quiz.core.Interface
     |      quiz.core.Object
     |      {}
     |
     |  Data descriptors defined here:
     |
     |  activeLockReason
     |      : LockReason or None
     |      Reason that the conversation was locked.
     |
     |  assignees
     |      : UserConnection
     |      A list of Users assigned to this object.
     |
     |  author
     |      : Actor or None
     |      The actor who authored the comment.
     |
     |  authorAssociation
     |      : CommentAuthorAssociation
     |      Author's association with the subject of the comment.
     |
     |  body
     |      : str
     |      Identifies the body of the issue.
     |
     |  bodyHTML
     |      : str
     |      Identifies the body of the issue rendered to HTML.
     |
     |  bodyText
     |      : str
     |      Identifies the body of the issue rendered to text.
     |
     |  closed
     |      : bool
     |      `true` if the object is closed (definition of closed may depend \
on type)
     |
     |  closedAt
     |      : datetime or None
     |      Identifies the date and time when the object was closed.
     |
     |  comments
     |      : IssueCommentConnection
     |      A list of comments associated with the Issue.
     |
     |  createdAt
     |      : datetime
     |      Identifies the date and time when the object was created.
     |
     |  createdViaEmail
     |      : bool
     |      Check if this comment was created via an email reply.
     |
     |  databaseId
     |      : int or None
     |      Identifies the primary key from the database.
     |
     |  editor
     |      : Actor or None
     |      The actor who edited the comment.
     |
     |  id
     |      : ID
     |      None
     |
     |  labels
     |      : LabelConnection or None
     |      A list of labels associated with the object.
     |
     |  lastEditedAt
     |      : datetime or None
     |      The moment the editor made the last edit
     |
     |  locked
     |      : bool
     |      `true` if the object is locked
     |
     |  milestone
     |      : Milestone or None
     |      Identifies the milestone associated with the issue.
     |
     |  number
     |      : int
     |      Identifies the issue number.
     |
     |  participants
     |      : UserConnection
     |      A list of Users that are participating in the Issue conversation.
     |
     |  projectCards
     |      : ProjectCardConnection
     |      List of project cards associated with this issue.
     |
     |  publishedAt
     |      : datetime or None
     |      Identifies when the comment was published at.
     |
     |  reactionGroups
     |      : [ReactionGroup] or None
     |      A list of reactions grouped by content left on the subject.
     |
     |  reactions
     |      : ReactionConnection
     |      A list of Reactions left on the Issue.
     |
     |  repository
     |      : Repository
     |      The repository associated with this node.
     |
     |  resourcePath
     |      : str
     |      The HTTP path for this issue
     |
     |  state
     |      : IssueState
     |      Identifies the state of the issue.
     |
     |  timeline
     |      : IssueTimelineConnection
     |      A list of events, comments, commits, etc. associated with \
the issue.
     |
     |  title
     |      : str
     |      Identifies the issue title.
     |
     |  updatedAt
     |      : datetime
     |      Identifies the date and time when the object was last updated.
     |
     |  url
     |      : str
     |      The HTTP URL for this issue
     |
     |  userContentEdits
     |      : UserContentEditConnection or None
     |      A list of edits to this content.
     |
     |  viewerCanReact
     |      : bool
     |      Can user react to this subject
     |
     |  viewerCanSubscribe
     |      : bool
     |      Check if the viewer is able to change their subscription status \
for the repository.
     |
     |  viewerCanUpdate
     |      : bool
     |      Check if the current viewer can update this object.
     |
     |  viewerCannotUpdateReasons
     |      : [CommentCannotUpdateReason]
     |      Reasons why the current viewer can not update this comment.
     |
     |  viewerDidAuthor
     |      : bool
     |      Did the viewer author this comment.
     |
     |  viewerSubscription
     |      : SubscriptionState
     |      Identifies if the viewer is watching, not watching, or ignoring \
the subscribable entity.
     |
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from quiz.core.Interface:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
    '''.format('{0.__module__}.{0.__name__}'.format(object))).strip()
    assert render_doc(classes['Issue']).strip() == expect


# TODO: more comprehensive tests
def test_get_schema(raw_schema):
    from ..helpers import MockClient

    client = MockClient(
        snug.Response(200, json.dumps({'data': raw_schema}).encode()))
    result = quiz.schema.get('https://my.url/graphql', scalars=EXAMPLE_SCALARS,
                             client=client)

    assert client.request.url == 'https://my.url/graphql'
    assert result['Query']
