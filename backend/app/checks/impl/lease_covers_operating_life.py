from datetime import timedelta

from app.checks.impl._values import add_years, as_date, as_number, condition_number
from app.checks.render import capitalise, number_word, short_date
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input


@check("lease_covers_operating_life")
def lease_covers_operating_life(inputs: dict[str, Input], view: GraphView) -> Outcome:
    lease = inputs["lease_term"]
    start = as_date(lease.value("start_date"))
    term = as_number(lease.value("term_years"))
    operating = inputs["operating_period"]
    years = as_number(operating.value("years"))
    first_export = as_date(inputs["first_export_proxy"].value("connection_date"))

    context: dict[str, object] = {}
    if operating.nodes and (number := condition_number(operating.nodes[0])):
        context["condition_number"] = number
    if start:
        context["lease_start_short"] = short_date(start)
    if term is not None:
        context["term_years"] = f"{term:g}"
    if years is not None:
        context["operating_years"] = f"{years:g}"
    if first_export:
        context["first_export_year"] = str(first_export.year)
    if not (start and term is not None and years is not None and first_export):
        return Outcome("pass", context)  # the runner reports what is missing

    # A term "from and including" the start date ends the day before the anniversary.
    lease_end = add_years(start, int(term)) - timedelta(days=1)
    operating_end = add_years(first_export, int(years))  # first export ~ grid connection
    shortfall = round((operating_end - lease_end).days / 365.25)
    context |= {
        "lease_end_year": str(lease_end.year),
        "operating_end_year": str(operating_end.year),
        "lease_end_short": short_date(lease_end),
        "shortfall_years": str(shortfall),
        "shortfall_years_word": number_word(shortfall),
        "shortfall_years_word_cap": capitalise(number_word(shortfall)),
    }
    return Outcome("fail" if lease_end < operating_end else "pass", context)
