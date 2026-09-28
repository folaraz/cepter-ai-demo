"""Prove the check templates reproduce the UI fixture wording exactly.

Usage (from the repo root):
    python backend/tools/check_templates.py

Needs: pip install pyyaml

For each check in backend/checks/, renders title, why, how, evidence roles, missing
evidence, RFI and summary strings using the hand-written context in
data/dataroom/planted_facts.yaml, and compares them with
design/api/fixtures/. If this passes, the only thing the check code has to
get right is computing the same context values from the graph.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = ROOT / "design" / "api" / "fixtures"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fmt(template: str, ctx: dict) -> str:
    return template.format(**ctx)


def main() -> int:
    checks = [load_yaml(p) for p in sorted((ROOT / "backend" / "checks").glob("*.yaml"))]
    planted = load_yaml(ROOT / "data" / "dataroom" / "planted_facts.yaml")
    summary = json.loads((EXPECTED / "summary.json").read_text(encoding="utf-8"))
    rfis = {r["check_id"]: r for r in json.loads((EXPECTED / "rfi.json").read_text(encoding="utf-8"))}
    failures: list[str] = []
    compared = 0

    def same(where: str, got: object, want: object) -> None:
        nonlocal compared
        compared += 1
        if got != want:
            failures.append(f"{where}\n   got:  {got!r}\n   want: {want!r}")

    orders = [c["order"] for c in checks]
    if orders != sorted(orders) or len(set(orders)) != len(orders):
        failures.append(f"check orders must be unique and match file order: {orders}")

    passed_titles = {p["check_id"]: p["title"] for p in summary["passed"]}
    for check in checks:
        cid = check["id"]
        key = planted["checks"][cid]
        ctx = key["context"]
        missing_ctx_keys = set(check.get("context", {})) - set(ctx)
        if missing_ctx_keys:
            failures.append(f"{cid}: planted context lacks {sorted(missing_ctx_keys)}")
            continue

        if key["result"] == "pass":
            same(f"{cid} passed title", check["title"]["passed"], passed_titles.get(cid))
            continue

        fid = f"F-{check['order']:02d}"
        same(f"{cid} finding id", fid, key["finding"])
        finding = json.loads((EXPECTED / "findings" / f"{fid}.json").read_text(encoding="utf-8"))
        same(f"{fid} check_id", finding["check_id"], cid)
        same(f"{fid} severity", finding["severity"], check["severity"])
        same(f"{fid} result", finding["result"], key["result"])
        same(f"{fid} title", fmt(check["title"]["flagged"], ctx), finding["title"])
        same(f"{fid} why", fmt(check["why"], ctx), finding["why"])
        same(f"{fid} how", fmt(check["how"], ctx), finding["how"])

        # Evidence order and roles
        got_pids = [e["citation"]["paragraph_id"] if e["kind"] == "quote" else "missing" for e in finding["evidence"]]
        same(f"{fid} evidence order", got_pids, key["evidence"])
        roles: dict[str, str] = {}
        for inp in check["inputs"]:
            if inp.get("evidence", True) is False:
                continue
            if "role_by_document" in inp:
                roles.update({f"doc:{d}": r for d, r in inp["role_by_document"].items()})
            elif "role" in inp:
                roles[inp["key"]] = fmt(inp["role"], ctx)
        quote_ev = [e for e in finding["evidence"] if e["kind"] == "quote"]
        if any(k.startswith("doc:") for k in roles):
            for e in quote_ev:
                same(f"{fid} role {e['citation']['paragraph_id']}", roles.get(f"doc:{e['citation']['document_id']}"), e["role"])
        else:
            want_roles = [r for k, r in roles.items() if not k.startswith("doc:")]
            same(f"{fid} roles", want_roles[: len(quote_ev)], [e["role"] for e in quote_ev])

        # Missing evidence
        miss_ev = [e for e in finding["evidence"] if e["kind"] == "missing"]
        if check.get("missing") and miss_ev:
            m = miss_ev[0]
            same(f"{fid} missing label", fmt(check["missing"]["label"], ctx), m["label"])
            same(f"{fid} missing note", fmt(check["missing"]["note"], ctx), m["note"])
            same(f"{fid} missing expected_by", cid, m["expected_by"])
            same(f"{fid} missing rfi_id", ctx.get("rfi_id"), m["rfi_id"])
        elif miss_ev:
            failures.append(f"{fid}: fixture has missing evidence but the check has no 'missing' block")

        # RFI
        if check.get("rfi") and key["result"] in ("missing_evidence", "conflict"):
            r = rfis.get(cid)
            if r is None:
                failures.append(f"{cid}: expected an RFI in rfi.json")
            else:
                same(f"{cid} rfi id", ctx.get("rfi_id"), r["id"])
                same(f"{cid} rfi finding", fid, r["finding_id"])
                same(f"{cid} rfi severity", check["severity"], r["severity"])
                same(f"{cid} rfi title", fmt(check["rfi"]["title"], ctx), r["title"])
                same(f"{cid} rfi request", fmt(check["rfi"]["request"], ctx), r["request"])
                same(f"{cid} rfi why", fmt(check["rfi"]["why"], ctx), r["why"])
                same(f"{cid} rfi documents", [fmt(d, ctx) for d in check["rfi"]["documents_expected"]], r["documents_expected"])
        elif cid in rfis:
            failures.append(f"{cid}: rfi.json has an RFI but the check defines none")

        # Summary strings
        if "long_horizon" in check:
            same(f"{cid} long_horizon text", fmt(check["long_horizon"]["text"], ctx), summary["long_horizon"]["text"])
            same(f"{cid} long_horizon flag", fmt(check["long_horizon"]["flag"], ctx), summary["long_horizon"]["flag"])
        if cid == "grid_before_cod":
            view = load_yaml(ROOT / "backend" / "summary_view.yaml")
            same("summary clash label", fmt(view["clash"]["label"], ctx), summary["clash"]["label"])
            same("summary clash days", ctx["days"], summary["clash"]["days"])

    # Headline
    flagged = [c for c in checks if planted["checks"][c["id"]]["result"] != "pass"]
    critical = [c for c in flagged if c["severity"] == "critical"]
    words = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    view = load_yaml(ROOT / "backend" / "summary_view.yaml")
    clause = view["headline"]["critical_clause"]["one"].format(phrase=critical[0]["headline_phrase"]) if len(critical) == 1 else ""
    same("summary headline", view["headline"]["template"].format(count_word=words[len(flagged)], critical_clause=clause), summary["headline"])

    # Summary facts and date marks: labels, order, tones and the finding each links to
    fid_of = {c["id"]: f"F-{c['order']:02d}" for c in checks}
    results = {cid: planted["checks"][cid]["result"] for cid in fid_of}
    same("summary fact keys", [f["key"] for f in view["facts"]], [f["key"] for f in summary["facts"]])
    for vf, sf in zip(view["facts"], summary["facts"]):
        same(f"fact {vf['key']} label", vf["label"], sf["label"])
        same(f"fact {vf['key']} finding", fid_of.get(vf["finding"]), sf["finding_id"])  # None: not clickable
    same("summary date keys", [d["key"] for d in view["dates"]], [d["key"] for d in summary["dates"]])
    for vd, sd in zip(view["dates"], summary["dates"]):
        same(f"date {vd['key']} label", vd["label"], sd["label"])
        same(f"date {vd['key']} finding", fid_of[vd["finding"]], sd["finding_id"])
        tone = vd["tone"]
        if isinstance(tone, dict):
            (rule, cid), = [(k, v) for k, v in tone.items() if k != "else"]
            tone = rule.split("_if_")[0] if results[cid] != "pass" else tone["else"]
        same(f"date {vd['key']} tone", tone, sd["tone"])
    same("summary checks_total", len(checks), summary["run"]["checks_total"])
    same("summary passed order", [c["id"] for c in checks if results[c["id"]] == "pass"], [p["check_id"] for p in summary["passed"]])
    want_missing = [
        {"label": fmt(c["missing"]["document_label"], planted["checks"][c["id"]]["context"]),
         "expected_by": c["id"], "rfi_id": planted["checks"][c["id"]]["context"].get("rfi_id"), "finding_id": fid_of[c["id"]]}
        for c in checks if c.get("missing") and results[c["id"]] == "missing_evidence"
    ]
    same("summary missing_documents", want_missing, summary["missing_documents"])

    # RFI order: missing evidence first (severity desc), then conflicts
    same("rfi order", [f"{r['id']} {r['check_id']}" for r in json.loads((EXPECTED / "rfi.json").read_text(encoding="utf-8"))], planted["rfi_order"])

    print(f"compared {compared} strings and fields")
    if failures:
        print("FAIL")
        for msg in failures:
            print(" -", msg)
        return 1
    print("PASS: templates reproduce the fixture wording exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
