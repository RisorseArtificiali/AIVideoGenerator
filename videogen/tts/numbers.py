"""Numbers in words, for the speech engines that do not read digits.

OmniVoice reads "0,042" as "zero zero forty-two": the text that it receives must have the
numbers in words. `spoken_tokens()` cuts a text in tokens (on the spaces) and gives, for each
token, the words that the voice reads. A token that is not a number gives itself. The tokens
keep their punctuation: the subtitles show the text as it was written, and each token receives
the time of its words.

Italian and English. In the other languages the digits stay as they are.
"""

from __future__ import annotations

import re
import string

from num2words import num2words

# The characters that can stay attached to a token, before or after its number.
EDGES = string.punctuation + "«»“”‘’…–—€£"
# A currency sign next to a number becomes a word after it: "$2,500" reads "two thousand dollars".
CURRENCY = {"it": {"$": "dollari", "€": "euro", "£": "sterline"}, "en": {"$": "dollars", "€": "euros", "£": "pounds"}}
# A token made only of a symbol, and the word that the voice reads. A dash or a quote alone is a pause.
SYMBOLS = {
    "it": {"&": "e", "+": "più", "=": "uguale", "×": "per", "n.": "numero"},
    "en": {"&": "and", "+": "plus", "=": "equals", "×": "times", "no.": "number"},
}
PERCENT = {"it": ["per", "cento"], "en": ["percent"]}
SEPARATOR = {"it": "virgola", "en": "point"}      # between the whole number and its decimals
MINUS = {"it": "meno", "en": "minus"}

# A range: two numbers with a dash between them.
RANGE = re.compile(r"(\d[\d.,]*)\s*[–—-]\s*(\d[\d.,]*)")
ORDINAL = {"it": re.compile(r"(\d+)[°º]"), "en": re.compile(r"(\d+)(st|nd|rd|th)")}
# The forms of one number, in the order of the verification.
FORMS = {
    "it": [
        ("thousands", re.compile(r"\d{1,3}(?:\.\d{3})+")),   # 38.000
        ("decimal", re.compile(r"\d+,\d+")),                # 3,61
        ("version", re.compile(r"\d+\.\d+")),               # 5.5
        ("integer", re.compile(r"\d+")),
    ],
    "en": [
        ("thousands", re.compile(r"\d{1,3}(?:,\d{3})+")),   # 38,000
        ("decimal", re.compile(r"\d+\.\d+")),               # 3.61
        ("integer", re.compile(r"\d+")),
    ],
}
ARTICLE = re.compile(r"([^\W\d_]+')(.+)")        # "l'1": an article with an apostrophe, then a number


def _cardinal(digits: str, language: str) -> list[str]:
    return num2words(int(digits), lang=language).split()


def _one_number(core: str, language: str) -> list[str] | None:
    """The words of one number, or None when `core` is not a number."""
    ordinal = ORDINAL[language].fullmatch(core)
    if ordinal:                                  # 96°, 1st
        return num2words(int(ordinal.group(1)), lang=language, to="ordinal").split()
    for kind, pattern in FORMS[language]:
        match = pattern.fullmatch(core)
        if not match:
            continue
        if kind in ("thousands", "integer"):
            return _cardinal(match.group(0).replace(".", "").replace(",", ""), language)
        whole, digits = match.group(0).split("," if language == "it" and kind != "version" else ".")
        # A version reads its separator "punto", also in Italian: "cinque punto cinque".
        words = _cardinal(whole, language) + ["punto" if kind == "version" else SEPARATOR[language]]
        if digits.startswith("0") or language == "en":
            # A zero after the separator is read digit by digit: "zero virgola zero quattro due".
            return words + [num2words(int(digit), lang=language) for digit in digits]
        return words + _cardinal(digits, language)
    return None


def words_of(token: str, language: str) -> list[str]:
    """The words that the voice reads for one token of a text. A token that is not a number
    gives itself; a symbol gives one word, or nothing when it is only a pause."""
    if language not in FORMS:
        return [token]
    start, end = 0, len(token)
    while start < end and token[start] in EDGES:
        start += 1
    while end > start and token[end - 1] in EDGES:
        end -= 1
    before, core, after = token[:start], token[start:end], token[end:]
    money, symbols = CURRENCY[language], SYMBOLS[language]
    if not core:                                 # only symbols: "dollari", "e", or a pause
        if token in money:
            return [money[token]]
        if token == "%":
            return PERCENT[language]
        return [symbols[token]] if token in symbols else []
    article, words = "", _one_number(core, language) or _range(core, language)
    if words is None and start == 0 and token in symbols:   # "n." before a number
        words = [symbols[token]]
    if words is None:
        match = ARTICLE.fullmatch(core)
        if match:
            article, words = match.group(1), _one_number(match.group(2), language)
    if words is None:
        return [token]
    # The signs around the number become words: "meno" before it, "per cento" and the currency after it.
    negative = before[-1:] in ("-", "−")
    before = before[:-1] if negative else before
    coins = [money[sign] for sign in before + after if sign in money]
    before = "".join(sign for sign in before if sign not in money)
    after = "".join(sign for sign in after if sign not in money and sign != "%")
    if "%" in token:
        words = words + PERCENT[language]
    words = words + coins
    if negative:
        words = [MINUS[language]] + words
    words[0] = article + before + words[0]
    words[-1] = words[-1] + after
    return words


def _range(core: str, language: str) -> list[str] | None:
    """A range such as "200-350": two numbers, with a short pause between them."""
    match = RANGE.fullmatch(core)
    if not match:
        return None
    first, second = _one_number(match.group(1), language), _one_number(match.group(2), language)
    if not first or not second:
        return None
    return first[:-1] + [first[-1] + ","] + second


def spoken_tokens(text: str, language: str) -> list[tuple[str, list[str]]]:
    """For each token of a text (cut on the spaces), the words that the voice reads.
    The words joined by a space are the text for the engine; the list gives the token of
    each group of words."""
    return [(token, words_of(token, language)) for token in text.split()]


def spoken_text(text: str, language: str) -> str:
    """The text with the numbers in words."""
    return " ".join(word for _token, words in spoken_tokens(text, language) for word in words)
