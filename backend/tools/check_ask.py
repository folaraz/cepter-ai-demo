"""Prove the Ask golden set is answerable (or unanswerable) from the data room.

Usage (from the repo root):
    python backend/tools/check_ask.py

Needs: pip install pymupdf pyyaml

Checks evals/ask_golden.jsonl against the ingested paragraphs, the answer key and
backend/ask.yaml:
  1. IDs are unique; routes, graph queries and params are ones ask.yaml allows.
  2. Lookup questions: every expected paragraph exists, every `answer_contains` string is
     stated in one of them (so a verified quote can support it), and no
     `answer_excludes` string is.
  3. Abstention questions: none of their `absent_terms` appears anywhere in the data room.
  4. Relationship questions: rendering the ask.yaml template from the answer key cites
     exactly the expected paragraphs and contains every `answer_contains` string.

It cannot test retrieval ranking or the model's lookup answers; `lens eval` does that.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_dataroom import ingest_all  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def display_name(name: str) -> str:
    """SPEC C6 display rule: companies lose the legal suffix; all-caps people get title case."""
    stripped = re.sub(r"\s+(limited|ltd\.?|plc|llp|lp)$", "", name.strip(), flags=re.I)
    if stripped != name.strip():
        return stripped
    return name.title() if name.isupper() else name


def render(query_id: str, params: dict, planted: dict, manifest: dict, ask: dict) -> tuple[str, set[str], dict]:
    q = ask["graph_queries"][query_id]
    prefix_to_doc = {d["paragraph_prefix"]: d for d in manifest["documents"]}
    sentences: list[str] = []
    cited: set[str] = set()
    meta: dict = {}

    def emit(tmpl: dict, ctx: dict, cites: list[str]) -> None:
        if "when" in tmpl and not ctx.get(tmpl["when"]):
            return
        sentences.append(tmpl["text"].format(**ctx))
        if tmpl.get("cite"):
            cited.update(cites)

    if "context_from_check" in q:
        check = q["context_from_check"]
        ctx = dict(planted["checks"][check]["context"])
        ctx.setdefault("all_covered", False)
        evid = [p for p in planted["checks"][check]["evidence"] if p != "missing"]
        by_input = {"cable_route": evid[:1], "land_rights": evid[1:2], "conditions": evid[:1]}
        for s in q["sentences"]:
            emit(s, ctx, [p for key in s.get("cite", []) for p in by_input.get(key, [])])
        fid = planted["checks"][check].get("finding")
        meta = {"related_finding_id": fid, "related_rfi_id": ctx.get("rfi_id")}
    elif query_id == "parties":
        agreement = params.get("agreement")
        for e in planted["edges"]:
            if e["type"] != "PARTY_TO" or (agreement and e["to"] != agreement):
                continue
            ctx = {"party": display_name(e["from"]), "role_label": q["role_labels"][e["role"]],
                   "agreement_phrase": q["agreement_phrases"][e["to"]]}
            emit(q["sentences"][0], ctx, [e["paragraph"]])
    elif query_id == "property_sources":
        prop = params["property"]
        node, name = prop.split(".")
        spec = q["params"]["property"]["allowed"][prop]
        facts = [f for f in planted["facts"] if f["node"] == node and f["property"] == name]
        counts: dict = {}
        for f in facts:
            counts[f["value"]] = counts.get(f["value"], 0) + 1
        facts.sort(key=lambda f: -counts[f["value"]])  # corroborated values first, stable within
        for f in facts:
            doc = prefix_to_doc[f["paragraph"].split(":")[0]]
            value = f"{f['value']:g}" if isinstance(f["value"], (int, float)) else str(f["value"])
            ctx = {"document_title_lower": doc["title"].lower(),
                   "value_text": f"{value} {spec['unit']}".strip()}
            emit(q["sentences"][0], ctx, [f["paragraph"]])
        emit(q["sentences"][1], {"conflict": len(counts) > 1}, [])
        meta = {"related_finding_id": f"F-{[c for c in planted['checks']].index(spec['check']) + 1:02d}"}
    else:
        raise KeyError(f"no renderer for graph query {query_id}")
    return " ".join(sentences), cited, meta


def main() -> int:
    paras = ingest_all()
    # Headings are part of every chunk's indexed text (ask.yaml chunk_text), so search them too.
    all_text = " ".join(f"{p.heading or ''} {p.text}" for p in paras.values()).lower()
    planted = yaml.safe_load((ROOT / "data/dataroom/planted_facts.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((ROOT / "data/dataroom/manifest.yaml").read_text(encoding="utf-8"))
    ask = yaml.safe_load((ROOT / "backend/ask.yaml").read_text(encoding="utf-8"))
    items = [json.loads(line) for line in (ROOT / "evals/ask_golden.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    failures: list[str] = []
    counts = {"lookup": 0, "relationship": 0, "abstain": 0}

    ids = [i["id"] for i in items]
    if len(ids) != len(set(ids)):
        failures.append("duplicate ids")
    for it in items:
        where = it["id"]
        if it["route"] not in ask["routing"]["routes"]:
            failures.append(f"{where}: unknown route {it['route']}")
        for pid in it.get("paragraphs", []):
            if pid not in paras:
                failures.append(f"{where}: paragraph {pid} does not exist")
        if it["expect"] == "abstain":
            counts["abstain"] += 1
            for term in it.get("absent_terms", []):
                if re.search(rf"\b{re.escape(term.lower())}\b", all_text):
                    failures.append(f"{where}: '{term}' appears in the data room, so abstaining would be wrong")
            continue
        if it["route"] == "lookup":
            counts["lookup"] += 1
            texts = [paras[p].text for p in it["paragraphs"] if p in paras]
            for s in it.get("answer_contains", []):
                if not any(s in t for t in texts):
                    failures.append(f"{where}: '{s}' is not stated in {it['paragraphs']}")
            for s in it.get("answer_excludes", []):
                if any(re.search(rf"\b{re.escape(s)}\b", t) for t in texts):
                    failures.append(f"{where}: excluded '{s}' appears in the expected paragraph")
        elif it["route"] == "relationship":
            counts["relationship"] += 1
            gq = it.get("graph_query")
            if gq not in ask["graph_queries"]:
                failures.append(f"{where}: unknown graph query {gq}")
                continue
            allowed = ask["graph_queries"][gq]["params"]
            for k, v in it.get("params", {}).items():
                spec = allowed.get(k)
                ok = spec is not None and (v in spec["allowed"])
                if not ok:
                    failures.append(f"{where}: param {k}={v!r} not allowed for {gq}")
            text, cited, meta = render(gq, it.get("params", {}), planted, manifest, ask)
            if cited != set(it["paragraphs"]):
                failures.append(f"{where}: cites {sorted(cited)}, expected {sorted(it['paragraphs'])}")
            for s in it.get("answer_contains", []):
                if s not in text:
                    failures.append(f"{where}: rendered answer lacks '{s}'\n   answer: {text}")
            for k in ("related_finding_id", "related_rfi_id"):
                if k in it and meta.get(k) != it[k]:
                    failures.append(f"{where}: {k} {meta.get(k)!r} != {it[k]!r}")
            print(f"  {where} [{gq}] {text}")

    # UI fixtures in design/api/fixtures/ask/ must agree with the golden set, the data room
    # and ask.yaml, so fixture mode never shows something the backend wouldn't.
    fx_dir = ROOT / "design" / "api" / "fixtures" / "ask"
    fx_checked = 0
    if fx_dir.exists():
        by_id = {i["id"]: i for i in items}
        want_sugg = [{"id": i["id"], "question": i["question"], "route": i["route"]} for i in items if i.get("suggested")]
        got_sugg = json.loads((fx_dir / "suggestions.json").read_text(encoding="utf-8"))
        if got_sugg != want_sugg:
            failures.append("fixtures/ask/suggestions.json differs from the suggested golden questions")
        messages = set(ask["messages"].values())
        rendered = {i["id"]: render(i["graph_query"], i.get("params", {}), planted, manifest, ask)[0]
                    for i in items if i["route"] == "relationship"}
        for f in sorted(fx_dir.glob("*.json")):
            if f.name == "suggestions.json":
                continue
            fx = json.loads(f.read_text(encoding="utf-8"))
            fx_checked += 1
            where = f"fixtures/ask/{f.name}"
            if fx["status"] != "answered":
                if fx["message"] not in messages:
                    failures.append(f"{where}: message is not one of ask.yaml messages")
                continue
            for s in fx["sentences"]:
                if not s["citations"] and not s["finding_id"]:
                    failures.append(f"{where}: a sentence has neither citations nor finding_id")
                for c in s["citations"]:
                    pid = c["citation"]["paragraph_id"]
                    p = paras.get(pid)
                    if p is None or c["paragraph_text"] != p.text or c["heading"] != p.heading or c["citation"]["page"] != p.page:
                        failures.append(f"{where}: citation {pid} does not match the data room")
                    elif c["paragraph_text"][c["quote_start"]:c["quote_end"]] != c["citation"]["quote"]:
                        failures.append(f"{where}: quote offsets wrong for {pid}")
                if fx["route"] == "lookup":
                    for num in re.findall(r"\d+(?:\.\d+)?", s["text"]):
                        if not any(num in c["citation"]["quote"] for c in s["citations"]):
                            failures.append(f"{where}: '{num}' in a sentence is not in its quotes")
            gid = f.stem
            if gid in rendered:
                text = " ".join(s["text"] for s in fx["sentences"])
                if text != rendered[gid]:
                    failures.append(f"{where}: wording differs from the ask.yaml template\n   got:  {text}\n   want: {rendered[gid]}")
            if gid in by_id and by_id[gid]["expect"] == "answer":
                cited = {c["citation"]["paragraph_id"] for s in fx["sentences"] for c in s["citations"]}
                if cited != set(by_id[gid]["paragraphs"]):
                    failures.append(f"{where}: cites {sorted(cited)}, golden expects {by_id[gid]['paragraphs']}")

    print(f"checked {len(items)} questions: {counts['lookup']} lookup, {counts['relationship']} relationship, {counts['abstain']} abstain; "
          f"{sum(1 for i in items if i.get('suggested'))} suggested; {fx_checked} UI fixtures")
    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: every Ask golden question is answerable (or unanswerable) as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
