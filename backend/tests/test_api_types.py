"""C10: the Pydantic models in app/api/models.py mirror design/api/types.ts.

Every exported interface must have a model of the same name with the same fields, the
same optional and nullable fields, arrays where the TypeScript has arrays, the same
primitive kinds, and the same values for every string-literal union. Known, deliberate
differences are listed in DEVIATIONS with their reason.

Ask's types (design/api/ask.types.ts) join the check when C14 adds their models.
"""

import re
from dataclasses import dataclass
from typing import Any, Literal, get_args

import pytest
from pydantic import BaseModel

from app.api import models
from app.config import REPO_ROOT
from app.domain.findings import Result, Severity

TYPES_TS = REPO_ROOT / "design" / "api" / "types.ts"
ASK_TYPES_TS = REPO_ROOT / "design" / "api" / "ask.types.ts"

# Models the API doesn't have yet, and the component that adds them.
PENDING: dict[str, str] = {}

# (interface, field) -> why the API differs from types.ts on purpose.
DEVIATIONS = {
    ("Summary", "clash"): "null when the grid connection does not clash with the PPA",
    ("Summary", "long_horizon"): "null when the lease covers the operating life",
}

# Request bodies: an optional field may also accept null.
REQUESTS = {"ReviewRequest", "AskRequest"}

PYTHON_UNIONS = {
    "Severity": get_args(Severity),
    "CheckResult": get_args(Result),
    "ReviewState": get_args(models.ReviewState),
    "QuoteStatus": get_args(models.QuoteStatus),
    "EvalState": get_args(models.EvalState),
    "AskRoute": get_args(models.AskRoute),
    "AskStatus": get_args(models.AskStatus),
}


# ---------- reading the TypeScript ----------


@dataclass(frozen=True)
class TsField:
    name: str
    type: str  # without "| null"
    optional: bool  # name?:
    nullable: bool  # ... | null


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


def _block(src: str, start: int) -> tuple[str, int]:
    """The text inside the braces opening at src[start], and the index after them."""
    depth = 0
    for i in range(start, len(src)):
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        if depth == 0:
            return src[start + 1 : i], i + 1
    raise ValueError("unbalanced braces")


def _split_top(text: str, sep: str) -> list[str]:
    """Split on `sep` outside braces and parentheses."""
    parts, depth, current = [], 0, ""
    for ch in text:
        depth += {"{": 1, "(": 1, "}": -1, ")": -1}.get(ch, 0)
        if ch == sep and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def parse_fields(body: str) -> list[TsField]:
    fields = []
    for member in _split_top(body.replace("\n", " "), ";"):
        name, _, type_ = member.partition(":")
        name, type_ = name.strip(), type_.strip()
        alternatives = _split_top(type_, "|")
        nullable = "null" in alternatives
        fields.append(
            TsField(
                name=name.rstrip("?"),
                type=" | ".join(a for a in alternatives if a != "null"),
                optional=name.endswith("?"),
                nullable=nullable,
            )
        )
    return fields


def parse_ts(*paths: Any) -> tuple[dict[str, list[TsField]], dict[str, list[str]]]:
    """Interfaces (with inherited fields) and string-literal union aliases."""
    src = "\n".join(_strip_comments(p.read_text(encoding="utf-8")) for p in paths)
    interfaces: dict[str, list[TsField]] = {}
    for m in re.finditer(r"export interface (\w+)(?: extends (\w+))?\s*\{", src):
        body, _ = _block(src, m.end() - 1)
        inherited = interfaces.get(m.group(2), []) if m.group(2) else []
        interfaces[m.group(1)] = inherited + parse_fields(body)
    unions = {
        m.group(1): re.findall(r'"([^"]+)"', m.group(2))
        for m in re.finditer(r"export type (\w+)\s*=\s*([^;]+);", src)
        if '"' in m.group(2)
    }
    return interfaces, unions


INTERFACES, UNIONS = parse_ts(TYPES_TS, ASK_TYPES_TS)


# ---------- comparing with a JSON schema ----------


def _resolve(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        schema = defs[schema["$ref"].split("/")[-1]]
    return schema


def _without_null(schema: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    options = schema.get("anyOf")
    if options and {"type": "null"} in options:
        rest = [o for o in options if o != {"type": "null"}]
        return (rest[0] if len(rest) == 1 else {"anyOf": rest}), True
    return schema, False


def compare_type(
    where: str, ts_type: str, schema: dict[str, Any], defs: dict[str, Any], problems: list[str]
) -> None:
    schema = _resolve(schema, defs)
    ts_type = ts_type.strip()
    if ts_type.endswith("[]"):
        if schema.get("type") != "array":
            problems.append(f"{where}: TypeScript has an array, the API {schema.get('type')}")
            return
        compare_type(where + "[]", ts_type[:-2], schema["items"], defs, problems)
        return
    if ts_type.startswith("{"):
        compare_object(where, parse_fields(_block(ts_type, 0)[0]), schema, defs, problems)
        return
    literals = re.findall(r'"([^"]+)"', ts_type)
    if ts_type in UNIONS or literals:
        want = set(UNIONS.get(ts_type, literals))
        got = set(schema.get("enum", [])) | ({schema["const"]} if "const" in schema else set())
        if got != want:
            problems.append(f"{where}: values {sorted(got)} != {sorted(want)}")
        return
    primitive = {"string": {"string"}, "number": {"number", "integer"}, "boolean": {"boolean"}}
    if ts_type in primitive:
        if schema.get("type") not in primitive[ts_type]:
            problems.append(f"{where}: {ts_type} in TypeScript, {schema.get('type')} in the API")
        return
    if ts_type in INTERFACES:
        compare_object(where, INTERFACES[ts_type], schema, defs, problems)
        return
    if " | " in ts_type:  # a union of interfaces, such as Evidence
        options = [_resolve(o, defs) for o in schema.get("anyOf", schema.get("oneOf", []))]
        names = [t.strip() for t in ts_type.split("|")]
        if len(options) != len(names):
            problems.append(
                f"{where}: {len(names)} alternatives in TypeScript, {len(options)} in the API"
            )
        for name, option in zip(names, options, strict=False):
            compare_type(f"{where}<{name}>", name, option, defs, problems)
        return
    if ts_type in ("Evidence",):
        compare_type(where, "QuoteEvidence | MissingEvidence", schema, defs, problems)
        return
    problems.append(f"{where}: unknown TypeScript type {ts_type!r}")


def compare_object(
    where: str,
    fields: list[TsField],
    schema: dict[str, Any],
    defs: dict[str, Any],
    problems: list[str],
    request: bool = False,
) -> None:
    schema = _resolve(schema, defs)
    props, required = schema.get("properties", {}), set(schema.get("required", []))
    ts_names = {f.name for f in fields}
    if set(props) != ts_names:
        extra, missing = sorted(set(props) - ts_names), sorted(ts_names - set(props))
        problems.append(f"{where}: API has extra {extra}, lacks {missing}")
    for f in fields:
        if f.name not in props:
            continue
        at = f"{where}.{f.name}"
        interface = where.split(".")[0]
        field_schema, nullable = _without_null(props[f.name])
        if (interface, f.name) in DEVIATIONS:
            continue
        if f.optional == (f.name in required):
            problems.append(
                f"{at}: optional in TypeScript is {f.optional}, in the API {not f.optional}"
            )
        if nullable != f.nullable and not (request and f.optional and nullable):
            problems.append(f"{at}: nullable in TypeScript is {f.nullable}, in the API {nullable}")
        compare_type(at, f.type, field_schema, defs, problems)


def model_problems(name: str) -> list[str]:
    model: type[BaseModel] = getattr(models, name)
    mode: Literal["validation", "serialization"] = (
        "validation" if name in REQUESTS else "serialization"
    )
    schema = model.model_json_schema(by_alias=True, mode=mode)
    problems: list[str] = []
    compare_object(
        name, INTERFACES[name], schema, schema.get("$defs", {}), problems, name in REQUESTS
    )
    return problems


# ---------- tests ----------

CHECKED = sorted(name for name in INTERFACES if name not in PENDING)


def test_the_reader_finds_every_declaration() -> None:
    assert len(INTERFACES) == 20 and set(UNIONS) >= set(PYTHON_UNIONS) | {"AskRoute", "AskStatus"}
    assert [f.name for f in INTERFACES["Finding"]][-3:] == ["why", "how", "evidence"]
    [corrected] = [f for f in INTERFACES["ReviewRequest"] if f.name == "corrected_result"]
    assert corrected.optional and not corrected.nullable


@pytest.mark.parametrize("name", CHECKED)
def test_model_mirrors_the_typescript(name: str) -> None:
    assert hasattr(models, name), f"app/api/models.py has no {name}"
    assert model_problems(name) == []


@pytest.mark.parametrize("name", sorted(PYTHON_UNIONS))
def test_enums_match(name: str) -> None:
    assert list(PYTHON_UNIONS[name]) == UNIONS[name]


def test_pending_models_are_still_pending() -> None:
    """Remove a name from PENDING when its model lands, so it is checked from then on."""
    assert [n for n in PENDING if hasattr(models, n)] == []


def test_the_checker_catches_drift() -> None:
    class FindingRow(BaseModel):  # a field renamed and a nullable dropped
        id: str

    schema = FindingRow.model_json_schema()
    problems: list[str] = []
    compare_object("FindingRow", INTERFACES["FindingRow"], schema, {}, problems)
    assert problems and "lacks" in problems[0]

    tone = next(f for f in INTERFACES["DateMark"] if f.name == "tone")
    bad: list[str] = []
    compare_type("DateMark.tone", tone.type, {"enum": ["neutral", "clash"]}, {}, bad)
    assert bad == ["DateMark.tone: values ['clash', 'neutral'] != ['clash', 'neutral', 'warning']"]
