"""The accuracy-check status shown on the Summary.

Until the eval harness exists (C11) there is no run to report, so the status says so:
"stale" with nothing measured yet.
"""

from app.api.models import EvalStatus
from app.config import REPO_ROOT, get_settings

GOLDEN = REPO_ROOT / "evals" / "golden.jsonl"


def current_eval_status(run_at: str) -> EvalStatus:
    golden = sum(1 for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip())
    return EvalStatus(
        state="stale",
        score=0.0,
        gate=get_settings().eval_gate,
        golden_count=golden,
        corrections_held=0,
        corrections_total=0,
        citation_validity=0.0,
        cost_gbp=0.0,
        last_run_at=run_at,
    )
