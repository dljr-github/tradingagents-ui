"""SQLite database operations for TradingAgents UI."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent.parent / "tradingagents_ui.db"
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pending',
                rating TEXT,
                config_json TEXT,
                market_report TEXT,
                sentiment_report TEXT,
                news_report TEXT,
                fundamentals_report TEXT,
                debate_history TEXT,
                risk_history TEXT,
                final_decision TEXT,
                full_state_json TEXT
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_runs_ticker ON runs(ticker);
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
            CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);
        """)


# --- Runs ---

def create_run(ticker: str, trade_date: str, config: dict) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO runs (ticker, trade_date, status, config_json) VALUES (?, ?, 'pending', ?)",
            (ticker.upper(), trade_date, json.dumps(config)),
        )
        return cur.lastrowid


def update_run_status(run_id: int, status: str):
    with get_db() as conn:
        conn.execute("UPDATE runs SET status = ? WHERE id = ?", (status, run_id))


def complete_run(run_id: int, rating: str, state: dict):
    invest_debate = state.get("investment_debate_state", {})
    risk_debate = state.get("risk_debate_state", {})
    with get_db() as conn:
        conn.execute(
            """UPDATE runs SET
                status = 'completed',
                completed_at = ?,
                rating = ?,
                market_report = ?,
                sentiment_report = ?,
                news_report = ?,
                fundamentals_report = ?,
                debate_history = ?,
                risk_history = ?,
                final_decision = ?,
                full_state_json = ?
            WHERE id = ?""",
            (
                datetime.now().isoformat(),
                rating,
                state.get("market_report", ""),
                state.get("sentiment_report", ""),
                state.get("news_report", ""),
                state.get("fundamentals_report", ""),
                json.dumps(invest_debate) if invest_debate else "",
                json.dumps(risk_debate) if risk_debate else "",
                state.get("final_trade_decision", ""),
                _safe_serialize_state(state),
                run_id,
            ),
        )


def fail_run(run_id: int, error: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE runs SET status = 'failed', final_decision = ? WHERE id = ?",
            (f"ERROR: {error}", run_id),
        )


def get_run(run_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None


def get_runs(
    ticker: Optional[str] = None,
    status: Optional[str] = None,
    rating: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    query = "SELECT * FROM runs WHERE 1=1"
    params = []
    if ticker:
        query += " AND ticker = ?"
        params.append(ticker.upper())
    if status:
        query += " AND status = ?"
        params.append(status)
    if rating:
        query += " AND rating = ?"
        params.append(rating)
    if date_from:
        query += " AND trade_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND trade_date <= ?"
        params.append(date_to)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_active_runs() -> list[dict]:
    return get_runs(status="running") + get_runs(status="pending")


# --- Watchlist ---

def add_to_watchlist(ticker: str, notes: str = ""):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, notes) VALUES (?, ?)",
            (ticker.upper(), notes),
        )


def remove_from_watchlist(ticker: str):
    with get_db() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))


def get_watchlist() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]


def is_in_watchlist(ticker: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM watchlist WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
        return row is not None


def _safe_serialize_state(state: dict) -> str:
    """Serialize state to JSON, dropping non-serializable fields."""
    clean = {}
    for k, v in state.items():
        if k == "messages":
            continue  # skip LangChain message objects
        try:
            json.dumps(v)
            clean[k] = v
        except (TypeError, ValueError):
            clean[k] = str(v)
    return json.dumps(clean)
