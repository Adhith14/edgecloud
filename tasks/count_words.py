def count_words(text):
    import re
    words = re.findall(r'[a-zA-Z]+', text.lower())
    word_freq = {word: words.count(word) for word in set(words)}
    return word_freq

# Example: count_words('Hello, world!') returns {'hello': 1, 'world': 1}