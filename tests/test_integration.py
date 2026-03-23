"""Integration tests for TradingAgents UI."""

import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core import database as db


class TestWatchlistToAnalysisWorkflow:
    """Test full workflow: add to watchlist -> get_quick_stats -> queue analysis."""

    def test_watchlist_to_run(self, tmp_db, mock_yfinance):
        from core import screener_data

        screener_data._ticker_info_cache.clear()
        screener_data._indicator_series_cache.clear()

        # 1. Add to watchlist
        db.add_to_watchlist("AAPL", notes="Watch for earnings")
        assert db.is_in_watchlist("AAPL")

        # 2. Get quick stats
        stats = screener_data.get_quick_stats("AAPL")
        assert "error" not in stats
        assert stats["price"] > 0

        # 3. Queue analysis run
        run_id = db.create_run("AAPL", "2025-03-15", {"model": "test"})
        assert run_id > 0

        # 4. Verify run is active
        active = db.get_active_runs()
        assert any(r["id"] == run_id for r in active)

        # 5. Complete the run
        state = {
            "market_report": "Bullish",
            "sentiment_report": "Positive",
            "final_trade_decision": "BUY",
        }
        db.complete_run(run_id, "BUY", state)

        # 6. Verify completion
        run = db.get_run(run_id)
        assert run["status"] == "completed"
        assert run["rating"] == "BUY"


class TestAlertsWorkflow:
    """Test alerts workflow: create -> check -> verify trigger."""

    def test_alert_lifecycle(self, tmp_db):
        from core import alerts

        # 1. Create an alert
        aid = alerts.create_alert("AAPL", "price", "above", 100.0)
        assert aid > 0

        # 2. Verify it's active
        active_alerts = alerts.get_alerts(enabled_only=True)
        assert len(active_alerts) == 1

        # 3. Check alerts with mock data
        mock_stats = {
            "ticker": "AAPL",
            "price": 190.0,
            "rsi": 55.0,
            "change_pct": 1.5,
            "volume": 30_000_000,
        }
        with patch("core.alerts.get_quick_stats", return_value=mock_stats):
            triggered = alerts.check_alerts()

        # 4. Verify trigger
        assert len(triggered) == 1
        assert triggered[0]["current_value"] == 190.0

        # 5. Verify triggered_at was set
        alert = alerts.get_alerts()[0]
        assert alert["triggered_at"] is not None

        # 6. Disable the alert
        new_state = alerts.toggle_alert(aid)
        assert new_state is False

        # 7. Delete the alert
        alerts.delete_alert(aid)
        assert len(alerts.get_alerts()) == 0


class TestPortfolioWorkflow:
    """Test portfolio workflow: add -> calculate stats -> remove."""

    def test_portfolio_lifecycle(self, tmp_db):
        from core import portfolio

        # 1. Add positions
        p1 = portfolio.add_position("AAPL", 10, 150.0, "2025-01-15")
        p2 = portfolio.add_position("MSFT", 5, 400.0, "2025-02-01")
        assert len(portfolio.get_positions()) == 2

        # 2. Calculate stats with mock prices
        def mock_price(ticker):
            return {"AAPL": 190.0, "MSFT": 420.0}.get(ticker)

        with patch("core.portfolio.get_ticker_price", side_effect=mock_price):
            stats = portfolio.calculate_portfolio_stats()

        assert len(stats) == 2
        aapl_stats = next(s for s in stats if s["ticker"] == "AAPL")
        assert aapl_stats["pnl"] > 0  # gained value

        # 3. Get summary
        with patch("core.portfolio.get_ticker_price", side_effect=mock_price):
            summary = portfolio.get_portfolio_summary()

        assert summary["position_count"] == 2
        assert summary["total_pnl"] > 0

        # 4. Remove a position
        portfolio.remove_position(p1)
        assert len(portfolio.get_positions()) == 1

        # 5. Remove remaining
        portfolio.remove_position(p2)
        assert len(portfolio.get_positions()) == 0


class TestViewModulesImport:
    """Test that all view modules can be imported without error."""

    @pytest.mark.parametrize("module_name", [
        "views.icons",
        "views.alerts",
        "views.history",
        "views.news",
        "views.results",
        "views.screener",
        "views.screener_charts",
        "views.screener_technical",
        "views.comparison",
        "views.portfolio",
        "views.analysis",
        "views.settings",
    ])
    def test_import(self, module_name):
        mod = importlib.import_module(module_name)
        assert mod is not None


class TestCoreModulesImport:
    """Test that all core modules can be imported without error."""

    @pytest.mark.parametrize("module_name", [
        "core.database",
        "core.alerts",
        "core.portfolio",
        "core.screener_data",
        "core.news",
        "core.export",
        "core.config",
        "core.theme",
        "core.progress",
        "core.earnings",
    ])
    def test_import(self, module_name):
        mod = importlib.import_module(module_name)
        assert mod is not None


class TestStaticAssets:
    """Test that CSS files exist and are non-empty."""

    def test_style_css_exists(self):
        css_path = Path(__file__).parent.parent / "static" / "style.css"
        assert css_path.exists()
        assert css_path.stat().st_size > 0

    def test_style_light_css_exists(self):
        css_path = Path(__file__).parent.parent / "static" / "style_light.css"
        assert css_path.exists()
        assert css_path.stat().st_size > 0
