import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config

STATUSES = ("pending_approval", "approved", "published", "rejected", "failed", "needs_assets")


class Store:
    def __init__(self, path: str | None = None):
        path = path or config.DB_PATH
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT NOT NULL,
            created TEXT NOT NULL, scheduled_at TEXT, published_at TEXT,
            topic TEXT, payload TEXT NOT NULL, error TEXT)"""
        )

    def add(self, status: str, payload: dict, scheduled_at: str | None = None) -> int:
        cur = self.db.execute(
            "INSERT INTO posts(status,created,scheduled_at,topic,payload) VALUES(?,?,?,?,?)",
            (status, _now(), scheduled_at, payload.get("plan", {}).get("topic"), json.dumps(payload, ensure_ascii=False)),
        )
        self.db.commit()
        return cur.lastrowid

    def get(self, post_id: int) -> dict:
        row = self.db.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not row:
            raise KeyError(post_id)
        return {**dict(row), "payload": json.loads(row["payload"])}

    def set_status(self, post_id: int, status: str, error: str | None = None):
        extra = ", published_at=?" if status == "published" else ""
        args = [status, error] + ([_now()] if extra else []) + [post_id]
        self.db.execute(f"UPDATE posts SET status=?, error=?{extra} WHERE id=?", args)
        self.db.commit()

    def update_payload(self, post_id: int, payload: dict):
        self.db.execute("UPDATE posts SET payload=? WHERE id=?", (json.dumps(payload, ensure_ascii=False), post_id))
        self.db.commit()

    def list(self, status: str | None = None) -> "list[dict]":
        q, a = "SELECT id,status,topic,scheduled_at,published_at FROM posts", ()
        if status:
            q, a = q + " WHERE status=?", (status,)
        return [dict(r) for r in self.db.execute(q + " ORDER BY id DESC", a)]

    def recent_topics(self) -> "list[str]":
        rows = self.db.execute("SELECT topic FROM posts WHERE status!='rejected' ORDER BY id DESC LIMIT 30").fetchall()
        return [r["topic"] for r in rows if r["topic"]]

    def published_today(self) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        return self.db.execute(
            "SELECT COUNT(*) c FROM posts WHERE status='published' AND published_at LIKE ?", (today + "%",)
        ).fetchone()["c"]

    def due(self) -> "list[dict]":
        now = _now()
        rows = self.db.execute(
            "SELECT id FROM posts WHERE status='approved' AND (scheduled_at IS NULL OR scheduled_at<=?) ORDER BY id", (now,)
        ).fetchall()
        return [self.get(r["id"]) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
