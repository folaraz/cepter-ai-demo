"""`nodes`, `edges` and `provenance`."""

from psycopg import Connection
from psycopg.rows import class_row

from app.db.repositories import params
from app.domain.graph import Edge, NewEdge, NewProvenance, Node, Provenance


def insert_nodes(conn: Connection, nodes: list[Node]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO nodes (id, run_id, type, key, name, props) "
            "VALUES (%(id)s, %(run_id)s, %(type)s, %(key)s, %(name)s, %(props)s)",
            [params(n, "props") for n in nodes],
        )


def list_nodes(conn: Connection, run_id: str) -> list[Node]:
    with conn.cursor(row_factory=class_row(Node)) as cur:
        cur.execute("SELECT * FROM nodes WHERE run_id = %s ORDER BY id", (run_id,))
        return cur.fetchall()


def insert_edge(conn: Connection, edge: NewEdge) -> Edge:
    with conn.cursor(row_factory=class_row(Edge)) as cur:
        cur.execute(
            "INSERT INTO edges (run_id, type, source_id, target_id, props) "
            "VALUES (%(run_id)s, %(type)s, %(source_id)s, %(target_id)s, %(props)s) "
            "RETURNING *",
            params(edge, "props"),
        )
        row = cur.fetchone()
    assert row is not None
    return row


def list_edges(conn: Connection, run_id: str) -> list[Edge]:
    with conn.cursor(row_factory=class_row(Edge)) as cur:
        cur.execute("SELECT * FROM edges WHERE run_id = %s ORDER BY id", (run_id,))
        return cur.fetchall()


def insert_provenance(conn: Connection, rows: list[NewProvenance]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO provenance (run_id, node_id, edge_id, property, value, claim_id,
                                    document_id, paragraph_id, quote, quote_start, quote_end,
                                    status)
            VALUES (%(run_id)s, %(node_id)s, %(edge_id)s, %(property)s, %(value)s, %(claim_id)s,
                    %(document_id)s, %(paragraph_id)s, %(quote)s, %(quote_start)s,
                    %(quote_end)s, %(status)s)
            """,
            [params(p, "value") for p in rows],
        )


def list_provenance(conn: Connection, run_id: str) -> list[Provenance]:
    with conn.cursor(row_factory=class_row(Provenance)) as cur:
        cur.execute("SELECT * FROM provenance WHERE run_id = %s ORDER BY id", (run_id,))
        return cur.fetchall()
