import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connection(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=30) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL, spec TEXT NOT NULL, result TEXT, error TEXT)""")
        yield db


def enqueue(path, spec):
    run_id = str(uuid.uuid4())
    with connection(path) as db:
        db.execute("INSERT INTO runs(id,status,spec) VALUES(?,?,?)",
                   (run_id, "queued", json.dumps(spec)))
    return run_id


def claim(path):
    with connection(path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM runs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
        if row:
            db.execute("UPDATE runs SET status='running' WHERE id=?", (row["id"],))
            return dict(row)


def finish(path, run_id, result=None, error=None):
    with connection(path) as db:
        db.execute("UPDATE runs SET status=?,result=?,error=? WHERE id=?",
                   ("failed" if error else "completed", json.dumps(result), error, run_id))


def list_runs(path):
    with connection(path) as db:
        rows = db.execute("SELECT * FROM runs ORDER BY created_at DESC,id DESC LIMIT 100").fetchall()
        return [dict(r) | {"spec": json.loads(r["spec"]), "result": json.loads(r["result"] or "null")}
                for r in rows]
