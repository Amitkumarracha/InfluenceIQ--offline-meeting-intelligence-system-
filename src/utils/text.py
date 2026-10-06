"""Unicode words for Hindi, English and romanized Hindi, without model imports."""
import unicodedata


def normalize_text(text):
    return unicodedata.normalize('NFKC', text).casefold().replace('’', "'")


def words(text):
    # Regex \w excludes combining marks: it splits हिंदी into broken fragments.
    current = []
    for char in normalize_text(text):
        category = unicodedata.category(char)[0]
        if category in {'L', 'N'} or (category == 'M' and current):
            current.append(char)
        elif current:
            yield ''.join(current)
            current = []
    if current:
        yield ''.join(current)
