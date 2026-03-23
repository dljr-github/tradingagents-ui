"""Unit tests for core/screener_data.py."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from core import screener_data


class TestGetQuickStats:
    def test_returns_correct_fields(self, mock_yfinance):
        # Clear caches before test
        screener_data._ticker_info_cache.clear()
        screener_data._indicator_series_cache.clear()

        stats = screener_data.get_quick_stats("AAPL")
        assert "error" not in stats
        assert stats["ticker"] == "AAPL"
        assert isinstance(stats["price"], float)
        assert isinstance(stats["change_pct"], float)
        assert isinstance(stats["volume"], int)
        assert stats["name"] == "Apple Inc."
        assert stats["sector"] == "Technology"
        # RSI should be between 0-100
        if stats["rsi"] is not None:
            assert 0 <= stats["rsi"] <= 100
        # SMAs should be present given 252 days of data
        assert stats["sma50"] is not None
        assert stats["sma200"] is not None

    def test_returns_macd_fields(self, mock_yfinance):
        screener_data._ticker_info_cache.clear()
        screener_data._indicator_series_cache.clear()

        stats = screener_data.get_quick_stats("AAPL")
        assert "macd_line" in stats
        assert "signal_line" in stats
        assert "macd_histogram" in stats

    def test_returns_bollinger_bands(self, mock_yfinance):
        screener_data._ticker_info_cache.clear()
        screener_data._indicator_series_cache.clear()

        stats = screener_data.get_quick_stats("AAPL")
        assert "bb_upper" in stats
        assert "bb_middle" in stats
        assert "bb_lower" in stats
        if stats["bb_upper"] is not None:
            assert stats["bb_upper"] > stats["bb_lower"]

    def test_returns_atr(self, mock_yfinance):
        screener_data._ticker_info_cache.clear()
        screener_data._indicator_series_cache.clear()

        stats = screener_data.get_quick_stats("AAPL")
        assert "atr" in stats
        if stats["atr"] is not None:
            assert stats["atr"] > 0

    def test_empty_history_returns_error(self):
        mock_inst = MagicMock()
        mock_inst.history.return_value = pd.DataFrame()
        with patch("yfinance.Ticker", return_value=mock_inst):
            stats = screener_data.get_quick_stats("FAKE")
        assert "error" in stats

    def test_exception_returns_error(self):
        with patch("yfinance.Ticker", side_effect=Exception("API error")):
            stats = screener_data.get_quick_stats("FAKE")
        assert "error" in stats


class TestGetTopMovers:
    def test_returns_gainers_losers_volume(self, mock_yfinance):
        screener_data._ticker_info_cache.clear()
        result = screener_data.get_top_movers(n=3)
        assert "gainers" in result
        assert "losers" in result
        assert "volume" in result

    def test_empty_on_download_failure(self):
        with patch("yfinance.download", side_effect=Exception("fail")), \
             patch("core.screener_data.get_ticker_info_cached", return_value={"name": "X", "sector": ""}):
            result = screener_data.get_top_movers()
        assert result == {"gainers": [], "losers": [], "volume": []}


class TestGetSectorPerformance:
    def test_returns_sorted_results(self, mock_yfinance):
        # We need to build a proper multi-ticker frame for sector ETFs
        from tests.conftest import _make_history_df
        etfs = list(screener_data.SECTOR_ETFS.values())
        dfs = {etf: _make_history_df(days=5, base_price=50) for etf in etfs}
        arrays = []
        for etf in etfs:
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                arrays.append((etf, col))
        multi_idx = pd.MultiIndex.from_tuples(arrays)
        combined = pd.concat([dfs[etf] for etf in etfs], axis=1)
        combined.columns = multi_idx

        with patch("yfinance.download", return_value=combined):
            result = screener_data.get_sector_performance()

        assert isinstance(result, list)
        if len(result) > 1:
            # Should be sorted descending by change_pct
            for i in range(len(result) - 1):
                assert result[i]["change_pct"] >= result[i + 1]["change_pct"]

    def test_download_failure_returns_empty(self):
        with patch("yfinance.download", side_effect=Exception("fail")):
            result = screener_data.get_sector_performance()
        assert result == []


class TestGetTickerInfoCached:
    def test_caches_result(self, mock_yfinance):
        screener_data._ticker_info_cache.clear()
        info1 = screener_data.get_ticker_info_cached("AAPL")
        info2 = screener_data.get_ticker_info_cached("AAPL")
        assert info1 == info2
        # Ticker constructor should only be called once for the cached call
        assert mock_yfinance["Ticker"].call_count == 1

    def test_returns_expected_fields(self, mock_yfinance):
        screener_data._ticker_info_cache.clear()
        info = screener_data.get_ticker_info_cached("AAPL")
        assert info["name"] == "Apple Inc."
        assert info["sector"] == "Technology"
        assert info["industry"] == "Consumer Electronics"
        assert info["market_cap"] == 3_000_000_000_000


class TestGetTickerPrice:
    def test_returns_price(self, mock_yfinance):
        price = screener_data.get_ticker_price("AAPL")
        assert isinstance(price, float)
        assert price > 0

    def test_empty_history_returns_none(self):
        mock_inst = MagicMock()
        mock_inst.history.return_value = pd.DataFrame()
        with patch("yfinance.Ticker", return_value=mock_inst):
            price = screener_data.get_ticker_price("FAKE")
        assert price is None

    def test_exception_returns_none(self):
        with patch("yfinance.Ticker", side_effect=Exception("fail")):
            price = screener_data.get_ticker_price("FAKE")
        assert price is None


class TestGetPriceHistory:
    def test_returns_dataframe(self, mock_yfinance):
        df = screener_data.get_price_history("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "Close" in df.columns

    def test_empty_on_failure(self):
        with patch("yfinance.Ticker", side_effect=Exception("fail")):
            df = screener_data.get_price_history("FAKE")
        assert df.empty
