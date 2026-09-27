from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class TradeLog:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    dry_run INTEGER NOT NULL,
                    ticker TEXT,
                    action TEXT,
                    side TEXT,
                    contracts INTEGER,
                    price TEXT,
                    cost TEXT,
                    edge REAL,
                    confidence REAL,
                    kelly REAL,
                    rationale TEXT,
                    result_json TEXT
                )
                """
            )

    def record(self, *, dry_run: bool, payload: dict, result: dict | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO decisions (
                    ts, dry_run, ticker, action, side, contracts, price, cost,
                    edge, confidence, kelly, rationale, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    1 if dry_run else 0,
                    payload.get("ticker"),
                    payload.get("action"),
                    payload.get("side"),
                    payload.get("contracts"),
                    str(payload.get("price")),
                    str(payload.get("cost")),
                    payload.get("edge"),
                    payload.get("confidence"),
                    payload.get("kelly"),
                    payload.get("rationale"),
                    json.dumps(result or {}, default=str),
                ),
            )
