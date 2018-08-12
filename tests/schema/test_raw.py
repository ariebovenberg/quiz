import quiz


# TODO: expand tests
def test_load(raw_schema):
    loaded = list(quiz.schema.load(raw_schema))
    assert loaded
