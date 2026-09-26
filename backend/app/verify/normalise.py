"""Text checks shared by the verifier (pass 2) and Ask's answer verification.

- find_quote: where a quote sits in a paragraph, allowing only differences that don't
  change what the text says (Unicode form, runs of whitespace, curly vs straight quotes).
- numbers_in / dates_in: the values a quote states, so a claimed value can be compared
  with them.
"""

import re
import unicodedata
from datetime import date

# One character for one character, so offsets in the normalised paragraph are offsets in
# the display text.
_QUOTE_MARKS = str.maketrans(
    {
        "\u2018": "'",  # left single
        "\u2019": "'",  # right single, the usual apostrophe
        "\u201a": "'",  # low single
        "\u201c": '"',  # left double
        "\u201d": '"',  # right double
        "\u201e": '"',  # low double
    }
)

MONTHS = {
    name: number
    for number, name in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        start=1,
    )
}

NUMBER_WORDS = {
    word: value
    for value, word in enumerate(
        [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ],
        start=1,
    )
} | {"thirty": 30, "forty": 40, "fifty": 50}

_NUMBER = re.compile(r"(?<![\d.])\d+(?:\.\d+)?")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")
_NUMBER_WORD = re.compile(r"\b(" + "|".join(NUMBER_WORDS) + r")\b", re.IGNORECASE)
_LONG_DATE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\b", re.IGNORECASE
)
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def normalise_quote(text: str) -> str:
    """NFKC, collapsed whitespace, straight quotes. Used on the model's quote."""
    return " ".join(unicodedata.normalize("NFKC", text).split()).translate(_QUOTE_MARKS)


def _normalise_paragraph(text: str) -> str:
    # Paragraph text is already NFKC with whitespace collapsed (ingestion does that), so
    # only the quote marks change here, character for character.
    return text.translate(_QUOTE_MARKS)


def find_quote(quote: str, paragraph_text: str) -> tuple[int, int] | None:
    """Offsets of the quote's first occurrence in the paragraph's display text, or None."""
    needle = normalise_quote(quote)
    if not needle:
        return None
    start = _normalise_paragraph(paragraph_text).find(needle)
    if start < 0:
        return None
    return start, start + len(needle)


def numbers_in(text: str) -> list[float]:
    """Every number the text states: digits (commas and currency ignored) and the words
    one to twenty, thirty, forty and fifty. "49.9MW" gives 49.9; "£4,850,000" 4850000."""
    digits = _THOUSANDS.sub("", text)
    found = [float(m) for m in _NUMBER.findall(digits)]
    found += [float(NUMBER_WORDS[w.casefold()]) for w in _NUMBER_WORD.findall(text)]
    return found


def dates_in(text: str) -> list[str]:
    """Every date the text states, as ISO strings: "1 October 2029" and "2029-10-01"."""
    found: list[str] = []
    for day, month, year in _LONG_DATE.findall(text):
        found += _iso(int(year), MONTHS[month.casefold()], int(day))
    for year, month, day in _ISO_DATE.findall(text):
        found += _iso(int(year), int(month), int(day))
    return found


def _iso(year: int, month: int, day: int) -> list[str]:
    try:
        return [date(year, month, day).isoformat()]
    except ValueError:
        return []


def same_number(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


def contains_text(haystack: str, needle: str) -> bool:
    """Case-insensitive, whitespace-normalised substring."""
    return " ".join(needle.casefold().split()) in " ".join(haystack.casefold().split())
