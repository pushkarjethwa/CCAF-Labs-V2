"""SQLite mock procurement database (GIVEN - do not edit).

Each server process builds its OWN in-memory database from DATA/procurement_seed.json, so every run
starts from identical state and approvals made in one process never leak into another."""
import json
import pathlib
import sqlite3

SEED = pathlib.Path(__file__).resolve().parent / "data" / "procurement_seed.json"

SCHEMA = """
CREATE TABLE suppliers (id TEXT PRIMARY KEY, name TEXT, category TEXT, status TEXT, country TEXT,
                        rating REAL, bank_account TEXT);
CREATE TABLE purchase_orders (id TEXT PRIMARY KEY, supplier_id TEXT REFERENCES suppliers(id), amount_cents INTEGER,
                              currency TEXT, status TEXT, requested_by TEXT, description TEXT);
CREATE TABLE approvals (seq INTEGER PRIMARY KEY, po_id TEXT REFERENCES purchase_orders(id), approver TEXT,
                        role TEXT, decision TEXT, comment TEXT);
"""


def connect() -> sqlite3.Connection:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    # check_same_thread=False: MCP runs sync tools in worker threads
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO suppliers VALUES (:id,:name,:category,:status,:country,:rating,:bank_account)", seed["suppliers"])
    con.executemany("INSERT INTO purchase_orders VALUES (:id,:supplier_id,:amount_cents,:currency,:status,:requested_by,:description)",
                    seed["purchase_orders"])
    con.executemany("INSERT INTO approvals (seq,po_id,approver,role,decision,comment) VALUES (:seq,:po_id,:approver,:role,:decision,:comment)",
                    seed["approvals"])
    con.commit()
    return con


def spend_limits() -> dict:
    """Role -> maximum PO amount (cents) that role may approve."""
    return json.loads(SEED.read_text(encoding="utf-8"))["spend_limits_cents"]


def mask_account(acct: str) -> str:
    return "****" + acct[-4:]


def supplier_row(con, supplier_id: str) -> dict | None:
    r = con.execute("SELECT * FROM suppliers WHERE id=?", (supplier_id,)).fetchone()
    return dict(r) if r else None


def search_suppliers(con, query: str, category: str | None, status: str | None, limit: int) -> list[dict]:
    sql, args = "SELECT * FROM suppliers WHERE lower(name) LIKE ?", [f"%{query.lower()}%"]
    if category:
        sql, args = sql + " AND category=?", args + [category]
    if status:
        sql, args = sql + " AND status=?", args + [status]
    sql += " ORDER BY id LIMIT ?"
    return [dict(r) for r in con.execute(sql, args + [max(1, min(limit, 50))])]


def po_row(con, po_id: str) -> dict | None:
    r = con.execute("SELECT * FROM purchase_orders WHERE id=?", (po_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["approvals"] = [dict(a) for a in con.execute(
        "SELECT seq, approver, role, decision, comment FROM approvals WHERE po_id=? ORDER BY seq", (po_id,))]
    return d


def record_decision(con, po_id: str, approver: str, role: str, comment: str) -> None:
    """Atomically mark a PENDING PO approved and append the approval row."""
    with con:
        cur = con.execute("UPDATE purchase_orders SET status='APPROVED' WHERE id=? AND status='PENDING'", (po_id,))
        if cur.rowcount != 1:
            raise RuntimeError("PO was not PENDING")
        con.execute("INSERT INTO approvals (po_id,approver,role,decision,comment) VALUES (?,?,?,?,?)",
                    (po_id, approver, role, "APPROVED", comment))
