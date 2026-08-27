def count_words(text):
    """
    Count the frequency of each word in a given text.

    Parameters:
        text (str): The input text to analyze.

    Returns:
        dict: A dictionary where keys are unique words and values are their frequencies.

    Example:
        >>> count_words('Hello, world! Hello everyone.')
        {'hello': 2, 'world': 1, 'everyone': 1}
    """
    import re
    words = re.findall(r'[a-zA-Z]+', text.lower())
    word_freq = {word: words.count(word) for word in words}
    return word_freq