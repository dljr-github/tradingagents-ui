"""Unit tests for core/alerts.py."""

from unittest.mock import patch

import pytest

from core import alerts


class TestCreateAlert:
    def test_create_price_alert(self, tmp_db):
        aid = alerts.create_alert("AAPL", "price", "above", 200.0)
        assert isinstance(aid, int)
        assert aid > 0

    def test_create_rsi_alert(self, tmp_db):
        aid = alerts.create_alert("MSFT", "rsi", "below", 30.0)
        assert aid > 0

    def test_create_change_pct_alert(self, tmp_db):
        aid = alerts.create_alert("TSLA", "change_pct", "above", 5.0)
        assert aid > 0

    def test_create_volume_alert(self, tmp_db):
        aid = alerts.create_alert("NVDA", "volume", "above", 50_000_000)
        assert aid > 0

    def test_invalid_metric_raises(self, tmp_db):
        with pytest.raises(ValueError, match="Invalid metric"):
            alerts.create_alert("AAPL", "pe_ratio", "above", 30.0)

    def test_invalid_operator_raises(self, tmp_db):
        with pytest.raises(ValueError, match="Invalid operator"):
            alerts.create_alert("AAPL", "price", "equals", 150.0)

    def test_ticker_uppercased(self, tmp_db):
        aid = alerts.create_alert("aapl", "price", "above", 200.0)
        result = alerts.get_alerts()
        assert result[0]["ticker"] == "AAPL"

    def test_crosses_above_operator(self, tmp_db):
        aid = alerts.create_alert("AAPL", "price", "crosses_above", 200.0)
        assert aid > 0

    def test_crosses_below_operator(self, tmp_db):
        aid = alerts.create_alert("AAPL", "rsi", "crosses_below", 30.0)
        assert aid > 0


class TestGetAlerts:
    def test_get_all(self, tmp_db):
        alerts.create_alert("AAPL", "price", "above", 200.0)
        alerts.create_alert("MSFT", "rsi", "below", 30.0)
        result = alerts.get_alerts()
        assert len(result) == 2

    def test_filter_by_ticker(self, tmp_db):
        alerts.create_alert("AAPL", "price", "above", 200.0)
        alerts.create_alert("MSFT", "rsi", "below", 30.0)
        result = alerts.get_alerts(ticker="AAPL")
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"

    def test_filter_enabled_only(self, tmp_db):
        a1 = alerts.create_alert("AAPL", "price", "above", 200.0)
        a2 = alerts.create_alert("MSFT", "rsi", "below", 30.0)
        alerts.toggle_alert(a2)  # disable
        result = alerts.get_alerts(enabled_only=True)
        assert len(result) == 1
        assert result[0]["id"] == a1


class TestDeleteAlert:
    def test_delete(self, tmp_db):
        aid = alerts.create_alert("AAPL", "price", "above", 200.0)
        alerts.delete_alert(aid)
        assert len(alerts.get_alerts()) == 0

    def test_delete_nonexistent(self, tmp_db):
        # Should not raise
        alerts.delete_alert(9999)


class TestToggleAlert:
    def test_toggle_disables(self, tmp_db):
        aid = alerts.create_alert("AAPL", "price", "above", 200.0)
        new_state = alerts.toggle_alert(aid)
        assert new_state is False

    def test_toggle_reenables(self, tmp_db):
        aid = alerts.create_alert("AAPL", "price", "above", 200.0)
        alerts.toggle_alert(aid)  # disable
        new_state = alerts.toggle_alert(aid)  # re-enable
        assert new_state is True

    def test_toggle_nonexistent_raises(self, tmp_db):
        with pytest.raises(ValueError, match="not found"):
            alerts.toggle_alert(9999)


class TestCheckAlerts:
    def test_above_triggered(self, tmp_db):
        alerts.create_alert("AAPL", "price", "above", 100.0)
        mock_stats = {"ticker": "AAPL", "price": 190.0, "rsi": 55.0, "change_pct": 1.5, "volume": 30_000_000}
        with patch("core.alerts.get_quick_stats", return_value=mock_stats):
            triggered = alerts.check_alerts()
        assert len(triggered) == 1
        assert triggered[0]["current_value"] == 190.0

    def test_below_triggered(self, tmp_db):
        alerts.create_alert("AAPL", "rsi", "below", 30.0)
        mock_stats = {"ticker": "AAPL", "price": 150.0, "rsi": 25.0, "change_pct": -2.0, "volume": 20_000_000}
        with patch("core.alerts.get_quick_stats", return_value=mock_stats):
            triggered = alerts.check_alerts()
        assert len(triggered) == 1
        assert triggered[0]["current_value"] == 25.0

    def test_not_triggered(self, tmp_db):
        alerts.create_alert("AAPL", "price", "above", 300.0)
        mock_stats = {"ticker": "AAPL", "price": 190.0, "rsi": 55.0, "change_pct": 1.5, "volume": 30_000_000}
        with patch("core.alerts.get_quick_stats", return_value=mock_stats):
            triggered = alerts.check_alerts()
        assert len(triggered) == 0

    def test_disabled_alert_not_checked(self, tmp_db):
        aid = alerts.create_alert("AAPL", "price", "above", 100.0)
        alerts.toggle_alert(aid)  # disable
        mock_stats = {"ticker": "AAPL", "price": 190.0, "rsi": 55.0, "change_pct": 1.5, "volume": 30_000_000}
        with patch("core.alerts.get_quick_stats", return_value=mock_stats):
            triggered = alerts.check_alerts()
        assert len(triggered) == 0

    def test_error_stats_skipped(self, tmp_db):
        alerts.create_alert("AAPL", "price", "above", 100.0)
        with patch("core.alerts.get_quick_stats", return_value={"ticker": "AAPL", "error": "No data"}):
            triggered = alerts.check_alerts()
        assert len(triggered) == 0

    def test_no_enabled_alerts_returns_empty(self, tmp_db):
        triggered = alerts.check_alerts()
        assert triggered == []

    def test_trigger_sets_triggered_at(self, tmp_db):
        aid = alerts.create_alert("AAPL", "price", "above", 100.0)
        mock_stats = {"ticker": "AAPL", "price": 190.0, "rsi": 55.0, "change_pct": 1.5, "volume": 30_000_000}
        with patch("core.alerts.get_quick_stats", return_value=mock_stats):
            alerts.check_alerts()
        result = alerts.get_alerts()
        assert result[0]["triggered_at"] is not None


class TestEvaluateCondition:
    def test_above(self):
        assert alerts._evaluate_condition(150.0, "above", 100.0, None) is True
        assert alerts._evaluate_condition(50.0, "above", 100.0, None) is False

    def test_below(self):
        assert alerts._evaluate_condition(50.0, "below", 100.0, None) is True
        assert alerts._evaluate_condition(150.0, "below", 100.0, None) is False

    def test_crosses_above(self):
        assert alerts._evaluate_condition(105.0, "crosses_above", 100.0, 95.0) is True
        assert alerts._evaluate_condition(105.0, "crosses_above", 100.0, 105.0) is False
        assert alerts._evaluate_condition(105.0, "crosses_above", 100.0, None) is False

    def test_crosses_below(self):
        assert alerts._evaluate_condition(95.0, "crosses_below", 100.0, 105.0) is True
        assert alerts._evaluate_condition(95.0, "crosses_below", 100.0, 90.0) is False
        assert alerts._evaluate_condition(95.0, "crosses_below", 100.0, None) is False

    def test_unknown_operator(self):
        assert alerts._evaluate_condition(100.0, "unknown", 100.0, None) is False


class TestGetMetricValue:
    def test_price(self):
        stats = {"price": 190.5, "rsi": 55.0, "change_pct": 1.5, "volume": 30_000_000}
        assert alerts._get_metric_value(stats, "price") == 190.5

    def test_error_returns_none(self):
        stats = {"error": "No data"}
        assert alerts._get_metric_value(stats, "price") is None

    def test_missing_metric_returns_none(self):
        stats = {"price": 190.5}
        assert alerts._get_metric_value(stats, "rsi") is None
