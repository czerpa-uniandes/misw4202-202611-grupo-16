from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "experiment_queue.db"


class OrderStore:
    """Persistencia mínima de órdenes procesadas para consultar /orders."""

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
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
                CREATE TABLE IF NOT EXISTS processed_orders (
                    order_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_order(self, order: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_orders(order_id, payload)
                VALUES (?, ?)
                """,
                (order["order_id"], json.dumps(order)),
            )

    def list_orders(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload, processed_at
                FROM processed_orders
                ORDER BY processed_at ASC
                """
            ).fetchall()

        output: list[dict[str, Any]] = []
        for row in rows:
            order = json.loads(row["payload"])
            order["processed_at"] = row["processed_at"]
            output.append(order)
        return output
