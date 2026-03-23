"""Unit tests for core/portfolio.py."""

from unittest.mock import patch

import pytest

from core import portfolio


class TestAddPosition:
    def test_add_position(self, tmp_db):
        pid = portfolio.add_position("AAPL", 10, 150.0, "2025-01-15", "Long position")
        assert isinstance(pid, int)
        assert pid > 0

    def test_default_entry_date(self, tmp_db):
        pid = portfolio.add_position("MSFT", 5, 400.0)
        positions = portfolio.get_positions()
        assert positions[0]["entry_date"] is not None

    def test_ticker_uppercased(self, tmp_db):
        portfolio.add_position("aapl", 10, 150.0)
        positions = portfolio.get_positions()
        assert positions[0]["ticker"] == "AAPL"


class TestGetPositions:
    def test_get_all(self, tmp_db):
        portfolio.add_position("AAPL", 10, 150.0)
        portfolio.add_position("MSFT", 5, 400.0)
        positions = portfolio.get_positions()
        assert len(positions) == 2

    def test_filter_by_ticker(self, tmp_db):
        portfolio.add_position("AAPL", 10, 150.0)
        portfolio.add_position("MSFT", 5, 400.0)
        positions = portfolio.get_positions(ticker="aapl")
        assert len(positions) == 1
        assert positions[0]["ticker"] == "AAPL"

    def test_empty(self, tmp_db):
        assert portfolio.get_positions() == []


class TestRemovePosition:
    def test_remove(self, tmp_db):
        pid = portfolio.add_position("AAPL", 10, 150.0)
        portfolio.remove_position(pid)
        assert len(portfolio.get_positions()) == 0

    def test_remove_nonexistent(self, tmp_db):
        # Should not raise
        portfolio.remove_position(9999)


class TestUpdatePosition:
    def test_update_quantity(self, tmp_db):
        pid = portfolio.add_position("AAPL", 10, 150.0)
        portfolio.update_position(pid, quantity=20)
        pos = portfolio.get_positions()[0]
        assert pos["quantity"] == 20

    def test_update_multiple_fields(self, tmp_db):
        pid = portfolio.add_position("AAPL", 10, 150.0)
        portfolio.update_position(pid, quantity=20, entry_price=155.0, notes="Updated")
        pos = portfolio.get_positions()[0]
        assert pos["quantity"] == 20
        assert pos["entry_price"] == 155.0
        assert pos["notes"] == "Updated"

    def test_update_no_fields(self, tmp_db):
        pid = portfolio.add_position("AAPL", 10, 150.0)
        portfolio.update_position(pid)  # no-op, should not raise


class TestCalculatePortfolioStats:
    def test_with_mock_prices(self, tmp_db):
        portfolio.add_position("AAPL", 10, 150.0)
        portfolio.add_position("MSFT", 5, 400.0)

        def mock_price(ticker):
            return {"AAPL": 190.0, "MSFT": 420.0}.get(ticker)

        with patch("core.portfolio.get_ticker_price", side_effect=mock_price):
            stats = portfolio.calculate_portfolio_stats()

        assert len(stats) == 2
        aapl = next(s for s in stats if s["ticker"] == "AAPL")
        assert aapl["current_price"] == 190.0
        assert aapl["market_value"] == 1900.0
        assert aapl["cost_basis"] == 1500.0
        assert aapl["pnl"] == 400.0
        assert aapl["pnl_pct"] == pytest.approx(26.67, abs=0.01)

    def test_price_unavailable(self, tmp_db):
        portfolio.add_position("AAPL", 10, 150.0)
        with patch("core.portfolio.get_ticker_price", return_value=None):
            stats = portfolio.calculate_portfolio_stats()
        assert stats[0]["current_price"] is None
        assert stats[0]["market_value"] is None
        assert stats[0]["pnl"] is None

    def test_empty_portfolio(self, tmp_db):
        with patch("core.portfolio.get_ticker_price"):
            stats = portfolio.calculate_portfolio_stats()
        assert stats == []


class TestGetPortfolioSummary:
    def test_with_positions(self, tmp_db):
        portfolio.add_position("AAPL", 10, 150.0)
        portfolio.add_position("MSFT", 5, 400.0)

        def mock_price(ticker):
            return {"AAPL": 190.0, "MSFT": 380.0}.get(ticker)

        with patch("core.portfolio.get_ticker_price", side_effect=mock_price):
            summary = portfolio.get_portfolio_summary()

        assert summary["position_count"] == 2
        assert summary["total_invested"] == 3500.0
        assert summary["total_value"] == 3800.0
        assert summary["total_pnl"] == 300.0
        assert summary["total_pnl_pct"] == pytest.approx(8.57, abs=0.01)
        assert summary["best_performer"]["ticker"] == "AAPL"
        assert summary["worst_performer"]["ticker"] == "MSFT"

    def test_empty_portfolio(self, tmp_db):
        summary = portfolio.get_portfolio_summary()
        assert summary["position_count"] == 0
        assert summary["total_invested"] == 0
        assert summary["total_value"] == 0
        assert summary["total_pnl"] == 0
        assert summary["best_performer"] is None
        assert summary["worst_performer"] is None

    def test_single_position(self, tmp_db):
        portfolio.add_position("AAPL", 10, 150.0)

        with patch("core.portfolio.get_ticker_price", return_value=200.0):
            summary = portfolio.get_portfolio_summary()

        assert summary["position_count"] == 1
        assert summary["best_performer"]["ticker"] == "AAPL"
        assert summary["worst_performer"]["ticker"] == "AAPL"
