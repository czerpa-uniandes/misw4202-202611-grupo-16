from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = DATA_DIR / "experiment_queue.db"


class FileBackedQueue:
    """Cola asíncrona mínima y persistente usando SQLite.

    Razón arquitectónica del experimento:
    - `cart_service` publica mensajes aquí (enqueue) sin depender de `order_service`.
    - `order_service` consume mensajes en background (dequeue + ack).
    - Si `order_service` cae, los mensajes quedan en estado `pending` en disco.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queued_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_status_id ON queued_messages(status, id)"
            )

    def enqueue(self, payload: dict[str, Any]) -> int:
        """Publica una orden en la cola y retorna el id de mensaje."""
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO queued_messages(payload, status) VALUES (?, 'pending')",
                (json.dumps(payload),),
            )
            return int(cur.lastrowid)

    def dequeue(self) -> tuple[int, dict[str, Any]] | None:
        """Toma 1 mensaje pendiente y lo marca como processing de forma atómica."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, payload FROM queued_messages WHERE status='pending' ORDER BY id LIMIT 1"
            ).fetchone()
            if row is None:
                return None

            updated = conn.execute(
                """
                UPDATE queued_messages
                SET status='processing', updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='pending'
                """,
                (row["id"],),
            )
            if updated.rowcount == 0:
                return None

            return int(row["id"]), json.loads(row["payload"])

    def ack(self, message_id: int) -> None:
        """Confirma mensaje procesado."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE queued_messages
                SET status='done', updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (message_id,),
            )

    def pending_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM queued_messages WHERE status='pending'"
            ).fetchone()
            return int(row["total"]) if row else 0
