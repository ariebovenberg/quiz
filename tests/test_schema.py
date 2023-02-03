import enum
import json
import pickle
import pydoc
import sys
import types

import pytest
import snug

import quiz
from quiz import SELECTOR as _
from quiz import schema as s

from .helpers import MockClient


def trim_whitespace(txt):
    return "".join(t.rstrip() + "\n" for t in txt.splitlines())


def render_doc(obj):
    return trim_whitespace(pydoc.render_doc(obj, renderer=pydoc.plaintext))


@pytest.fixture
def schema(raw_schema):
    return quiz.Schema.from_raw(raw_schema, module="mymodule")


class TestEnumAsType:
    def test_simple(self):
        enum_schema = s.Enum(
            "MyValues",
            "my enum!",
            values=[
                s.EnumValue(
                    "foo", "foo value...", True, "this is deprecated!"
                ),
                s.EnumValue("blabla", "...", False, None),
                s.EnumValue("qux", "qux value.", False, None),
            ],
        )
        created = s.enum_as_type(enum_schema, module="foo")
        assert issubclass(created, quiz.Enum)
        assert issubclass(created, enum.Enum)

        assert created.__name__ == "MyValues"
        assert created.__doc__ == "my enum!"
        assert created.__module__ == "foo"

        assert len(created.__members__) == 3

        for (name, member), member_schema in zip(
            created.__members__.items(), enum_schema.values
        ):
            assert name == member_schema.name
            assert member.name == name
            assert member.value == name
            assert member.__doc__ == member_schema.desc


class TestUnionAsType:
    def test_one(self):
        union_schema = s.Union(
            "Foo", "my union!", [s.TypeRef("BlaType", s.Kind.OBJECT, None)]
        )

        objs = {"BlaType": type("BlaType", (), {})}

        created = s.union_as_type(union_schema, objs)
        assert created.__name__ == "Foo"
        assert created.__doc__ == "my union!"
        assert issubclass(created, quiz.Union)

        assert created.__args__ == (objs["BlaType"],)

    def test_simple(self):
        union_schema = s.Union(
            "Foo",
            "my union!",
            [
                s.TypeRef("BlaType", s.Kind.OBJECT, None),
                s.TypeRef("Quxlike", s.Kind.INTERFACE, None),
                s.TypeRef("Foobar", s.Kind.UNION, None),
            ],
        )

        objs = {
            "BlaType": type("BlaType", (), {}),
            "Quxlike": type("Quxlike", (), {}),
            "Foobar": type("Foobar", (), {}),
            "Bla": type("Bla", (), {}),
        }

        created = s.union_as_type(union_schema, objs)
        assert created.__name__ == "Foo"
        assert created.__doc__ == "my union!"
        assert issubclass(created, quiz.Union)

        assert created.__args__ == (
            objs["BlaType"],
            objs["Quxlike"],
            objs["Foobar"],
        )


class TestInterfaceAsType:
    def test_simple(self):
        interface_schema = s.Interface(
            "Foo",
            "my interface!",
            [
                s.Field(
                    "blabla",
                    type=s.TypeRef("String", s.Kind.SCALAR, None),
                    args=[],
                    desc="my description",
                    is_deprecated=False,
                    deprecation_reason=None,
                )
            ],
        )
        created = s.interface_as_type(interface_schema, module="mymodule")

        assert isinstance(created, quiz.Interface)
        assert issubclass(created, quiz.types.Namespace)
        assert created.__name__ == "Foo"
        assert created.__doc__ == "my interface!"
        assert created.__module__ == "mymodule"


class TestObjectAsType:
    def test_simple(self):
        obj_schema = s.Object(
            "Foo",
            "the foo description!",
            interfaces=[
                s.TypeRef("Interface1", s.Kind.INTERFACE, None),
                s.TypeRef("BlaInterface", s.Kind.INTERFACE, None),
            ],
            input_fields=None,
            fields=[
                s.Field(
                    "blabla",
                    type=s.TypeRef("String", s.Kind.SCALAR, None),
                    args=[],
                    desc="my description",
                    is_deprecated=False,
                    deprecation_reason=None,
                )
            ],
        )
        interfaces = {
            "Interface1": type(
                "Interface1", (quiz.Interface,), {"__module__": "foo"}
            ),
            "BlaInterface": type(
                "BlaInterface", (quiz.Interface,), {"__module__": "foo"}
            ),
            "Qux": type("Qux", (quiz.Interface,), {"__module__": "foo"}),
        }
        created = s.object_as_type(obj_schema, interfaces, module="foo")
        assert issubclass(created, quiz.Object)
        assert created.__name__ == "Foo"
        assert created.__doc__ == "the foo description!"
        assert created.__module__ == "foo"
        assert issubclass(created, interfaces["Interface1"])
        assert issubclass(created, interfaces["BlaInterface"])


class TestResolveTypeRef:
    def test_default(self):
        ref = s.TypeRef("Foo", s.Kind.ENUM, None)

        classes = {"Foo": quiz.Enum("Foo", {})}
        resolved = s.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.Nullable)
        assert resolved.__arg__ is classes["Foo"]

    def test_non_null(self):
        ref = s.TypeRef(
            None, s.Kind.NON_NULL, s.TypeRef("Foo", s.Kind.OBJECT, None)
        )

        classes = {"Foo": type("Foo", (), {})}
        resolved = s.resolve_typeref(ref, classes)
        assert resolved == classes["Foo"]

    def test_list(self):
        ref = s.TypeRef(
            None, s.Kind.LIST, s.TypeRef("Foo", s.Kind.OBJECT, None)
        )
        classes = {"Foo": type("Foo", (), {})}
        resolved = s.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.Nullable)
        assert issubclass(resolved.__arg__, quiz.List)
        assert issubclass(resolved.__arg__.__arg__, quiz.Nullable)
        assert resolved.__arg__.__arg__.__arg__ == classes["Foo"]

    def test_list_non_null(self):
        ref = s.TypeRef(
            None,
            s.Kind.NON_NULL,
            s.TypeRef(
                None,
                s.Kind.LIST,
                s.TypeRef(
                    None,
                    s.Kind.NON_NULL,
                    s.TypeRef("Foo", s.Kind.OBJECT, None),
                ),
            ),
        )
        classes = {"Foo": type("Foo", (), {})}
        resolved = s.resolve_typeref(ref, classes)
        assert issubclass(resolved, quiz.List)
        assert resolved.__arg__ == classes["Foo"]


class TestSchemaFromRaw:
    def test_scalars(self, raw_schema):
        class URI(quiz.Scalar):
            pass

        schema = quiz.Schema.from_raw(raw_schema, scalars=[URI], module="foo")

        # generic scalars
        assert issubclass(schema.DateTime, quiz.GenericScalar)
        assert schema.DateTime.__name__ == "DateTime"
        assert len(schema.__doc__) > 0

        assert schema.Boolean is bool
        assert schema.String is str
        assert schema.Float is float
        assert schema.Int is int

        assert schema.URI is URI

    def test_defaults(self, raw_schema):
        schema = quiz.Schema.from_raw(raw_schema, module="foo")
        assert isinstance(schema, quiz.Schema)
        assert issubclass(schema.DateTime, quiz.GenericScalar)
        assert schema.String is str
        assert "Query" in schema.classes
        assert schema.query_type == schema.classes["Query"]
        assert schema.mutation_type == schema.classes["Mutation"]
        assert schema.subscription_type is None
        assert schema.raw == raw_schema


class TestSchema:
    def test_attributes(self, schema):
        assert schema.Query is schema.classes["Query"]
        assert schema.module == "mymodule"
        assert issubclass(schema.classes["Repository"], quiz.Object)
        assert "Repository" in dir(schema)
        assert "__class__" in dir(schema)

        with pytest.raises(AttributeError, match="foo"):
            schema.foo

    def test_populate_module(self, raw_schema, mocker):
        mymodule = types.ModuleType("mymodule")
        mocker.patch.dict(sys.modules, {"mymodule": mymodule})

        schema = quiz.Schema.from_raw(raw_schema, module="mymodule")

        with pytest.raises(AttributeError, match="Repository"):
            mymodule.Repository

        schema.populate_module()

        assert mymodule.Repository is schema.Repository

        my_obj = mymodule.Repository(description="...", name="my repo")
        loaded = pickle.loads(pickle.dumps(my_obj))
        assert loaded == my_obj

    def test_populate_module_no_module(self, raw_schema):
        schema = quiz.Schema.from_raw(raw_schema)
        assert schema.module is None

        with pytest.raises(RuntimeError, match="module"):
            schema.populate_module()

    def test_query(self, schema):
        query = schema.query[_.license(key="MIT")]
        assert query == quiz.Query(
            cls=schema.Query,
            selections=quiz.SelectionSet(
                quiz.Field("license", {"key": "MIT"})
            ),
        )
        with pytest.raises(quiz.SelectionError):
            schema.query[_.foo]

    def test_to_path(self, schema, tmpdir):
        path = str(tmpdir / "myschema.json")

        class MyPath(object):
            def __fspath__(self):
                return path

        schema.to_path(MyPath())
        loaded = schema.from_path(MyPath(), module="mymodule")
        assert loaded.classes.keys() == schema.classes.keys()


class TestSchemaFromUrl:
    def test_success(self, raw_schema):
        client = MockClient(
            snug.Response(
                200, json.dumps({"data": {"__schema": raw_schema}}).encode()
            )
        )
        result = quiz.Schema.from_url("https://my.url/graphql", client=client)

        assert client.request.url == "https://my.url/graphql"
        assert isinstance(result, quiz.Schema)
        assert result.raw == raw_schema

    def test_fails(self, raw_schema):
        client = MockClient(
            snug.Response(
                200,
                json.dumps(
                    {"data": {"__schema": None}, "errors": "foo"}
                ).encode(),
            )
        )

        with pytest.raises(quiz.ErrorResponse):
            quiz.Schema.from_url("https://my.url/graphql", client=client)

    @pytest.mark.live
    def test_live(self):  # pragma: no cover
        schema = quiz.Schema.from_url("https://graphqlzero.almansi.me/api")
        assert schema.User


class TestSchemaFromPath:
    def test_defaults(self, raw_schema, tmpdir):
        schema_file = tmpdir / "myfile.json"
        with schema_file.open("w") as wfile:
            json.dump(raw_schema, wfile)

        schema = quiz.Schema.from_path(schema_file)
        assert schema.module is None

    def test_success(self, raw_schema, tmpdir):
        schema_file = tmpdir / "myfile.json"
        with schema_file.open("w") as wfile:
            json.dump(raw_schema, wfile)

        class MyPath(object):
            def __fspath__(self):
                return str(schema_file)

        schema = quiz.Schema.from_path(MyPath(), module="mymodule")
        assert isinstance(schema, quiz.Schema)

    def test_does_not_exist(self, tmpdir):
        schema_file = tmpdir / "does-not-exist.json"

        with pytest.raises(IOError):
            quiz.Schema.from_path(str(schema_file), module="mymodule")


def test_end_to_end(raw_schema):
    schema = quiz.Schema.from_raw(raw_schema, module="github")
    doc = render_doc(schema.Issue)

    assert (
        """\
 |  viewerDidAuthor
 |      : bool
 |      Did the viewer author this comment."""
        in doc
    )
    assert (
        """\
 |  publishedAt
 |      : DateTime or None
 |      Identifies when the comment was published at."""
        in doc
    )

    assert (
        """\
 |  viewerCannotUpdateReasons
 |      : [CommentCannotUpdateReason]
 |      Reasons why the current viewer can not update this comment."""
        in doc
    )

    assert schema.Issue.__doc__ in doc
    assert "Labelable" in doc
