"""Unit tests for core/database.py."""

import json
from datetime import datetime, timedelta

import pytest

from core import database as db


class TestInitDb:
    def test_creates_all_tables(self, tmp_db):
        with db.get_db() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = sorted(r["name"] for r in tables)
        assert "alerts" in table_names
        assert "positions" in table_names
        assert "runs" in table_names
        assert "watchlist" in table_names

    def test_idempotent(self, tmp_db):
        # Calling init_db again should not raise
        db.init_db()
        with db.get_db() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        assert len([t for t in tables if t["name"] in ("runs", "watchlist", "alerts", "positions")]) == 4


class TestWatchlist:
    def test_add_and_get(self, tmp_db):
        db.add_to_watchlist("aapl", notes="My favorite")
        wl = db.get_watchlist()
        assert len(wl) == 1
        assert wl[0]["ticker"] == "AAPL"
        assert wl[0]["notes"] == "My favorite"

    def test_is_in_watchlist(self, tmp_db):
        assert not db.is_in_watchlist("AAPL")
        db.add_to_watchlist("AAPL")
        assert db.is_in_watchlist("aapl")  # case insensitive

    def test_remove(self, tmp_db):
        db.add_to_watchlist("MSFT")
        db.remove_from_watchlist("msft")
        assert not db.is_in_watchlist("MSFT")

    def test_duplicate_ignored(self, tmp_db):
        db.add_to_watchlist("TSLA")
        db.add_to_watchlist("TSLA")  # should not raise
        wl = db.get_watchlist()
        assert sum(1 for w in wl if w["ticker"] == "TSLA") == 1

    def test_remove_nonexistent(self, tmp_db):
        # Should not raise
        db.remove_from_watchlist("NONEXISTENT")

    def test_multiple_tickers(self, tmp_db):
        for t in ["AAPL", "MSFT", "GOOGL"]:
            db.add_to_watchlist(t)
        wl = db.get_watchlist()
        assert len(wl) == 3


class TestRuns:
    def test_create_run(self, tmp_db):
        run_id = db.create_run("aapl", "2025-01-15", {"model": "gpt-4"})
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_get_run(self, tmp_db):
        run_id = db.create_run("MSFT", "2025-02-01", {"model": "test"})
        run = db.get_run(run_id)
        assert run is not None
        assert run["ticker"] == "MSFT"
        assert run["trade_date"] == "2025-02-01"
        assert run["status"] == "pending"
        assert json.loads(run["config_json"]) == {"model": "test"}

    def test_get_run_not_found(self, tmp_db):
        assert db.get_run(9999) is None

    def test_update_run_status(self, tmp_db):
        run_id = db.create_run("NVDA", "2025-01-10", {})
        db.update_run_status(run_id, "running")
        run = db.get_run(run_id)
        assert run["status"] == "running"

    def test_complete_run(self, tmp_db):
        run_id = db.create_run("AAPL", "2025-03-01", {})
        state = {
            "market_report": "Bullish market",
            "sentiment_report": "Positive sentiment",
            "news_report": "Good news",
            "fundamentals_report": "Strong fundamentals",
            "investment_debate_state": {"round1": "buy"},
            "risk_debate_state": {"risk": "low"},
            "final_trade_decision": "BUY",
        }
        db.complete_run(run_id, "BUY", state)
        run = db.get_run(run_id)
        assert run["status"] == "completed"
        assert run["rating"] == "BUY"
        assert run["market_report"] == "Bullish market"
        assert run["final_decision"] == "BUY"
        assert run["completed_at"] is not None

    def test_fail_run(self, tmp_db):
        run_id = db.create_run("TSLA", "2025-01-20", {})
        db.fail_run(run_id, "API timeout")
        run = db.get_run(run_id)
        assert run["status"] == "failed"
        assert "API timeout" in run["final_decision"]

    def test_get_runs_no_filter(self, tmp_db):
        db.create_run("AAPL", "2025-01-01", {})
        db.create_run("MSFT", "2025-01-02", {})
        runs = db.get_runs()
        assert len(runs) == 2

    def test_get_runs_filter_by_ticker(self, tmp_db):
        db.create_run("AAPL", "2025-01-01", {})
        db.create_run("MSFT", "2025-01-02", {})
        runs = db.get_runs(ticker="aapl")
        assert len(runs) == 1
        assert runs[0]["ticker"] == "AAPL"

    def test_get_runs_filter_by_status(self, tmp_db):
        r1 = db.create_run("AAPL", "2025-01-01", {})
        r2 = db.create_run("MSFT", "2025-01-02", {})
        db.update_run_status(r1, "running")
        runs = db.get_runs(status="running")
        assert len(runs) == 1

    def test_get_runs_filter_by_date_range(self, tmp_db):
        db.create_run("AAPL", "2025-01-01", {})
        db.create_run("MSFT", "2025-06-15", {})
        db.create_run("GOOGL", "2025-12-31", {})
        runs = db.get_runs(date_from="2025-06-01", date_to="2025-07-01")
        assert len(runs) == 1
        assert runs[0]["ticker"] == "MSFT"

    def test_get_runs_limit(self, tmp_db):
        for i in range(10):
            db.create_run("AAPL", f"2025-01-{i+1:02d}", {})
        runs = db.get_runs(limit=3)
        assert len(runs) == 3

    def test_get_active_runs_includes_pending_and_running(self, tmp_db):
        r1 = db.create_run("AAPL", "2025-01-01", {})
        r2 = db.create_run("MSFT", "2025-01-02", {})
        db.update_run_status(r2, "running")
        active = db.get_active_runs()
        ids = {r["id"] for r in active}
        assert r1 in ids
        assert r2 in ids

    def test_get_active_runs_includes_recently_completed(self, tmp_db):
        r1 = db.create_run("AAPL", "2025-01-01", {})
        state = {"final_trade_decision": "BUY"}
        db.complete_run(r1, "BUY", state)
        # Recently completed should appear
        active = db.get_active_runs()
        ids = {r["id"] for r in active}
        assert r1 in ids

    def test_ticker_uppercased(self, tmp_db):
        run_id = db.create_run("aapl", "2025-01-01", {})
        run = db.get_run(run_id)
        assert run["ticker"] == "AAPL"


class TestSafeSerializeState:
    def test_drops_messages(self):
        state = {"market_report": "ok", "messages": ["msg1", "msg2"]}
        result = json.loads(db._safe_serialize_state(state))
        assert "messages" not in result
        assert result["market_report"] == "ok"

    def test_non_serializable_converted_to_str(self):
        state = {"obj": object()}
        result = json.loads(db._safe_serialize_state(state))
        assert isinstance(result["obj"], str)
