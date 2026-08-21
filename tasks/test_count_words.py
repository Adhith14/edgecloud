assert count_words('') == {}
assert count_words('Hello, world!') == {'hello': 1, 'world': 1}
assert count_words('The quick brown fox jumps over the lazy dog.') == {'the': 2, 'quick': 1, 'brown': 1, 'fox': 1, 'jumps': 1, 'over': 1, 'lazy': 1, 'dog': 1}