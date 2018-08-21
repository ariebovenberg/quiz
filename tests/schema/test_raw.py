import quiz


def test_load(raw_schema):
    loaded = list(quiz.schema.load(raw_schema))
    assert loaded
    assert isinstance(loaded[0], quiz.schema.raw.Scalar)
