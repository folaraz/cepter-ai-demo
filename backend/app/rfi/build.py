"""RFIs: what to ask the seller, one per open finding whose check defines a request.

Numbering is fixed when the run is checked (missing evidence first, then conflicts, each
by severity and order), because missing-evidence notes already quote it. An RFI is listed
while its finding is still missing evidence or in conflict for this visitor: a lawyer who
corrects the finding to a plain fail or a pass withdraws the question.
"""

from app.api.models import Rfi
from app.published import Published


def build_rfis(p: Published) -> list[Rfi]:
    rfis = []
    for f in p.findings:
        spec = p.specs[f.check_id]
        if spec.rfi is None or not f.rfi_id:
            continue
        if p.state[f.id].result not in ("missing_evidence", "conflict"):
            continue
        ctx = f.context
        rfis.append(
            Rfi(
                id=f.rfi_id,
                finding_id=f.id,
                check_id=f.check_id,
                title=spec.rfi.title.format(**ctx),
                severity=f.severity,
                request=spec.rfi.request.format(**ctx),
                why=spec.rfi.why.format(**ctx),
                documents_expected=[d.format(**ctx) for d in spec.rfi.documents_expected],
            )
        )
    return sorted(rfis, key=lambda r: r.id)
