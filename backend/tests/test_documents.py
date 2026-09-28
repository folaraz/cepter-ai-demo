"""The wording of planning-condition notes in the document reader (documents_view.yaml).
The notes themselves are compared exactly in tests/test_contract.py."""

from app.documents.build import _spec, condition_text

SPEC = _spec()["conditions"]


def test_a_condition_reads_as_the_obligation_it_puts_on_the_project() -> None:
    assert condition_text("time_limit", {"years": 3}, SPEC) == (
        "Work must start within 3 years of the permission"
    )
    assert condition_text(
        "pre_commencement", {"requires": "Construction Traffic Management Plan"}, SPEC
    ) == ("No work may start until the Construction Traffic Management Plan is approved")


def test_a_value_that_was_not_quoted_is_never_stated() -> None:
    assert condition_text("time_limit", {}, SPEC) == "Work must start within the time limit"
    assert condition_text("pre_commencement", {"requires": None}, SPEC) == (
        "No work may start until this condition is discharged"
    )


def test_a_discharge_on_file_is_said() -> None:
    text = condition_text("approved_plans", {"discharged_on": "2025-05-03"}, SPEC)
    assert text == "Build to the approved plans. Discharged 3 May 2025"


def test_an_unknown_type_still_reads_as_a_condition() -> None:
    assert condition_text("heritage", {}, SPEC) == "A condition of the planning permission"
