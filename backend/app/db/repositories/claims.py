"""`claims`."""

from psycopg import Connection
from psycopg.rows import class_row

from app.db.repositories import params
from app.domain.claims import Claim, ClaimStatus, NewClaim

_JSON = ("local_ref", "target_ref", "value")


def insert_claims(conn: Connection, claims: list[NewClaim]) -> list[Claim]:
    """Insert in order; the result carries each claim's new ID."""
    out: list[Claim] = []
    with conn.cursor(row_factory=class_row(Claim)) as cur:
        for claim in claims:
            cur.execute(
                """
                INSERT INTO claims (run_id, document_id, kind, local_ref, property, edge_type,
                                    target_ref, value, paragraph_id, quote, status,
                                    rejection_reason, quote_start, quote_end)
                VALUES (%(run_id)s, %(document_id)s, %(kind)s, %(local_ref)s, %(property)s,
                        %(edge_type)s, %(target_ref)s, %(value)s, %(paragraph_id)s, %(quote)s,
                        %(status)s, %(rejection_reason)s, %(quote_start)s, %(quote_end)s)
                RETURNING *
                """,
                params(claim, *_JSON),
            )
            row = cur.fetchone()
            assert row is not None
            out.append(row)
    return out


def list_claims(conn: Connection, run_id: str, status: ClaimStatus | None = None) -> list[Claim]:
    with conn.cursor(row_factory=class_row(Claim)) as cur:
        cur.execute(
            "SELECT * FROM claims WHERE run_id = %(run)s "
            "AND (%(status)s::text IS NULL OR status = %(status)s) ORDER BY id",
            {"run": run_id, "status": status},
        )
        return cur.fetchall()
