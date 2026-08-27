import count_words
def test_count_words():
    assert count_words.count_words('Hello, world! Hello everyone.') == {'hello': 2, 'world': 1, 'everyone': 1}
    assert count_words.count_words('') == {}
    assert count_words.count_words('123 456 789') == {} test_count_words()