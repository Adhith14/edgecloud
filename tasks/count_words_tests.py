def test_count_words():
    assert count_words('Hello, world!') == {'hello': 1, 'world': 1}
    assert count_words('This is a test. This is only a test.') == {'this': 2, 'is': 2, 'a': 2, 'test': 2}
    assert count_words('') == {}

test_count_words()