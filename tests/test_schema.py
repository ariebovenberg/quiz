import datetime
import enum
import json
import pydoc
import sys
import types
from textwrap import dedent

import pytest
import six
import snug

import quiz
from quiz import schema


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
        enum_schema = schema.Enum('MyValues', 'my enum!', values=[
            schema.EnumValue(
                'foo',
                'foo value...',
                True,
                'this is deprecated!'
            ),
            schema.EnumValue(
                'blabla',
                '...',
                False,
                None
            ),
            schema.EnumValue(
                'qux',
                'qux value.',
                False,
                None
            )
        ])
        created = schema.enum_as_type(enum_schema, module='foo')
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
        union_schema = schema.Union('Foo', 'my union!', [
            schema.TypeRef('BlaType', schema.Kind.OBJECT, None),
            schema.TypeRef('Quxlike', schema.Kind.INTERFACE, None),
            schema.TypeRef('Foobar', schema.Kind.UNION, None),
        ])

        objs = {
            'BlaType': type('BlaType', (), {}),
            'Quxlike': type('Quxlike', (), {}),
            'Foobar': type('Foobar', (), {}),
            'Bla': type('Bla', (), {}),
        }

        created = schema.union_as_type(union_schema, objs)
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
        interface_schema = schema.Interface('Foo', 'my interface!', [
            schema.Field(
                'blabla',
                type=schema.TypeRef('String', schema.Kind.SCALAR, None),
                args=[],
                desc='my description',
                is_deprecated=False,
                deprecation_reason=None,
            ),
        ])
        created = schema.interface_as_type(interface_schema,
                                           module='mymodule')

        assert isinstance(created, quiz.Interface)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'my interface!'
        assert created.__module__ == 'mymodule'


class TestObjectAsType:

    def test_simple(self):
        obj_schema = schema.Object(
            'Foo',
            'the foo description!',
            interfaces=[
                schema.TypeRef('Interface1', schema.Kind.INTERFACE, None),
                schema.TypeRef('BlaInterface', schema.Kind.INTERFACE, None),
            ],
            input_fields=None,
            fields=[
                schema.Field(
                    'blabla',
                    type=schema.TypeRef('String', schema.Kind.SCALAR, None),
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
        created = schema.object_as_type(obj_schema, interfaces,
                                        module='foo')
        assert issubclass(created, quiz.Object)
        assert created.__name__ == 'Foo'
        assert created.__doc__ == 'the foo description!'
        assert created.__module__ == 'foo'
        assert issubclass(created, interfaces['Interface1'])
        assert issubclass(created, interfaces['BlaInterface'])


class TestResolveTypeRef:

    def test_default(self):
        ref = schema.TypeRef('Foo', schema.Kind.ENUM, None)

        classes = {'Foo': quiz.Enum('Foo', {})}
        resolved = schema.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.Nullable)
        assert resolved.__arg__ is classes['Foo']

    def test_non_null(self):
        ref = schema.TypeRef(None, schema.Kind.NON_NULL,
                             schema.TypeRef('Foo', schema.Kind.OBJECT, None))

        classes = {'Foo': type('Foo', (), {})}
        resolved = schema.resolve_typeref(ref, classes)
        assert resolved == classes['Foo']

    def test_list(self):
        ref = schema.TypeRef(None, schema.Kind.LIST,
                             schema.TypeRef('Foo', schema.Kind.OBJECT, None))
        classes = {'Foo': type('Foo', (), {})}
        resolved = schema.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.Nullable)
        assert issubclass(resolved.__arg__, quiz.List)
        assert issubclass(resolved.__arg__.__arg__, quiz.Nullable)
        assert resolved.__arg__.__arg__.__arg__ == classes['Foo']

    def test_list_non_null(self):
        ref = schema.TypeRef(
            None, schema.Kind.NON_NULL,
            schema.TypeRef(
                None, schema.Kind.LIST,
                schema.TypeRef(
                    None, schema.Kind.NON_NULL,
                    schema.TypeRef('Foo', schema.Kind.OBJECT, None)
                )))
        classes = {'Foo': type('Foo', (), {})}
        resolved = schema.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.List)
        assert resolved.__arg__ == classes['Foo']


class TestBuild:

    def test_missing_scalars(self, raw_schema):
        with pytest.raises(Exception, match='DateTime'):
            quiz.schema.build(raw_schema, scalars={}, module='foo')

    def test_valid(self, raw_schema):
        schema = quiz.schema.build(raw_schema, scalars=EXAMPLE_SCALARS,
                                   module='mymodule')
        assert isinstance(schema, quiz.Schema)
        assert 'Query' in schema.classes
        assert schema.query_type == schema.classes['Query']
        assert schema.mutation_type == schema.classes['Mutation']
        assert schema.subscription_type is None


class TestSchema:

    def test_attributes(self, raw_schema):
        schema = quiz.schema.build(raw_schema, scalars=EXAMPLE_SCALARS,
                                   module='mymodule')
        assert schema.Query is schema.classes['Query']
        assert schema.module == 'mymodule'
        assert issubclass(schema.classes['Repository'], quiz.Object)
        assert 'Repository' in dir(schema)
        assert '__class__' in dir(schema)

        with pytest.raises(AttributeError, match='foo'):
            schema.foo

    def test_populate_module(self, raw_schema, mocker):
        mymodule = types.ModuleType('mymodule')
        mocker.patch.dict(sys.modules, {'mymodule': mymodule})

        schema = quiz.schema.build(raw_schema, module='mymodule',
                                   scalars=EXAMPLE_SCALARS)

        with pytest.raises(AttributeError, match='Repository'):
            mymodule.Repository

        schema.populate_module()

        assert mymodule.Repository is schema.Repository


def test_end_to_end(raw_schema):
    schema = quiz.schema.build(raw_schema, scalars={
        'URI':             str,
        'DateTime':        datetime.datetime,
        'HTML':            str,
        'GitObjectID':     str,
        'GitTimestamp':    str,
        'Date':            datetime.date,
        'X509Certificate': str,
        'GitSSHRemote':    str,
    }, module='github')
    expect = dedent('''
    Python Library Documentation: class Issue

    class Issue(Node, Assignable, Closable, Comment, Updatable, \
UpdatableComment, Labelable, Lockable, Reactable, RepositoryNode, \
Subscribable, UniformResourceLocatable, quiz.types.Object)
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
     |      quiz.types.Object
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
     |  Data descriptors inherited from Node:
     |
     |  __dict__
     |      dictionary for instance variables (if defined)
     |
     |  __weakref__
     |      list of weak references to the object (if defined)
    '''.format('{0.__module__}.{0.__name__}'.format(object))).strip()
    assert render_doc(schema.Issue).strip() == expect


# TODO: more comprehensive tests
def test_get_schema(raw_schema):
    from .helpers import MockClient

    client = MockClient(
        snug.Response(200, json.dumps({'data': raw_schema}).encode()))
    result = quiz.schema.get('https://my.url/graphql', scalars=EXAMPLE_SCALARS,
                             client=client)

    assert client.request.url == 'https://my.url/graphql'
    assert isinstance(result, quiz.Schema)
