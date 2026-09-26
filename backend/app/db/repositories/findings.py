"""`findings`."""

from psycopg import Connection
from psycopg.rows import class_row

from app.db.repositories import params
from app.domain.findings import FindingRecord


def insert_findings(conn: Connection, findings: list[FindingRecord]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO findings (run_id, id, check_id, severity, result, title, why, how,
                                  context, evidence, rfi_id)
            VALUES (%(run_id)s, %(id)s, %(check_id)s, %(severity)s, %(result)s, %(title)s,
                    %(why)s, %(how)s, %(context)s, %(evidence)s, %(rfi_id)s)
            """,
            [params(f, "context", "evidence") for f in findings],
        )


def get_finding(conn: Connection, run_id: str, finding_id: str) -> FindingRecord | None:
    with conn.cursor(row_factory=class_row(FindingRecord)) as cur:
        cur.execute("SELECT * FROM findings WHERE run_id = %s AND id = %s", (run_id, finding_id))
        return cur.fetchone()


def list_findings(conn: Connection, run_id: str) -> list[FindingRecord]:
    """In check order (F-01, F-02, ...)."""
    with conn.cursor(row_factory=class_row(FindingRecord)) as cur:
        cur.execute("SELECT * FROM findings WHERE run_id = %s ORDER BY id", (run_id,))
        return cur.fetchall()
