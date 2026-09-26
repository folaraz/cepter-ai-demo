"""Name normalisation, deterministic and without a model.

A name ending in a legal suffix is a company: "Brackenfield Solar Ltd" and "Brackenfield
Solar Limited" share the key "brackenfield solar". Anything else is a person, keyed by
surname and first initial, so "JOHN HARTLEY" and "Mr J. Hartley" are both "hartley:j".
The verifier (pass 2) and consolidation (pass 3) both use these rules.
"""

import re
from dataclasses import dataclass

LEGAL_SUFFIXES = ("limited", "ltd", "plc", "llp", "lp")
HONORIFICS = ("mr", "mrs", "ms", "dr", "sir")

_SUFFIX = re.compile(r"[\s,]+(?:" + "|".join(LEGAL_SUFFIXES) + r")\.?\s*$", re.IGNORECASE)
_HONORIFIC = re.compile(r"^(?:" + "|".join(HONORIFICS) + r")\.?\s+", re.IGNORECASE)
_PUNCTUATION = re.compile(r"[^\w\s]")


def is_company(name: str) -> bool:
    return bool(_SUFFIX.search(name.strip()))


def without_suffix(name: str) -> str:
    """ "Northwind Energy Supply Limited" -> "Northwind Energy Supply"."""
    return _SUFFIX.sub("", name.strip()).strip()


@dataclass(frozen=True)
class PersonName:
    first: str  # as written without punctuation: "John" or "J"
    surname: str

    @property
    def initial(self) -> str:
        return self.first[:1]


def person_name(name: str) -> PersonName | None:
    """First and last word after honorifics are removed; None if fewer than two words."""
    words = _PUNCTUATION.sub(" ", _HONORIFIC.sub("", name.strip())).split()
    if len(words) < 2:
        return None
    return PersonName(first=words[0], surname=words[-1])


def name_key(name: str) -> str:
    if is_company(name):
        return " ".join(_PUNCTUATION.sub(" ", without_suffix(name)).casefold().split())
    person = person_name(name)
    if person is None:
        return " ".join(_PUNCTUATION.sub(" ", name).casefold().split())
    return f"{person.surname.casefold()}:{person.initial.casefold()}"
