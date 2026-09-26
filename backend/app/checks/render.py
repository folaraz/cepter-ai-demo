"""Wording helpers for finding, summary and RFI text. Every template value that isn't a
raw number or a verbatim name goes through one of these, so the phrasing is identical
wherever it appears."""

from datetime import date

_WORDS = [
    "zero",
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
]


def short_date(d: date) -> str:
    """ "1 Oct 2029": day without a leading zero, abbreviated month."""
    return f"{d.day} {d:%b %Y}"


def number_word(n: int) -> str:
    """ "nine"; numbers past twenty stay as digits."""
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


def capitalise(text: str) -> str:
    """Upper-case the first letter only: "the PPA" stays "the PPA", "planning" -> "Planning"."""
    return text[:1].upper() + text[1:]


def join_prose(items: list[str]) -> str:
    """ "A", "A and B", "A, B and C"."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def format_number(value: float) -> str:
    """ "49.9", "45" (no trailing .0)."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def parcel_prose(numbers: list[int]) -> str:
    """ "Parcel 14", "Parcels 14 and 15", "Parcels 14, 15 and 16"."""
    ordered = sorted(numbers)
    label = "Parcel" if len(ordered) == 1 else "Parcels"
    return f"{label} {join_prose([str(n) for n in ordered])}"


def _runs(numbers: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for n in sorted(set(numbers)):
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return runs


def range_short(numbers: list[int]) -> str:
    """Runs of three or more as "9 to 11", the rest listed: "9 to 11", "9, 10 and 12"."""
    parts: list[str] = []
    for run in _runs(numbers):
        if len(run) >= 3:
            parts.append(f"{run[0]} to {run[-1]}")
        else:
            parts += [str(n) for n in run]
    return join_prose(parts)


def range_dash(numbers: list[int]) -> str:
    """Runs of two or more with an en dash: "14–15", "3–5 and 9"."""
    parts = [f"{r[0]}–{r[-1]}" if len(r) >= 2 else str(r[0]) for r in _runs(numbers)]
    return join_prose(parts)


def noun_list(nouns: list[str]) -> str:
    """Document nouns in running text, first letter capitalised: "Planning and the PPA"."""
    return capitalise(join_prose(nouns))
