def count_words(text):
    import re
    words = re.findall(r'[a-zA-Z]+', text.lower())
    word_freq = {}
    for word in words:
        if word in word_freq:
            word_freq[word] += 1
        else:
            word_freq[word] = 1
    return word_freq