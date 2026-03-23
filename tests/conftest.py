"""Shared fixtures for TradingAgents UI tests."""

import sqlite3
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Patch DB_PATH to a temp file and initialize the schema."""
    db_file = tmp_path / "test.db"

    # Patch DB_PATH in the database module
    import core.database as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", db_file)

    # Reset the thread-local connection so it picks up the new path
    if hasattr(db_mod._local, "conn") and db_mod._local.conn is not None:
        try:
            db_mod._local.conn.close()
        except Exception:
            pass
        db_mod._local.conn = None

    db_mod.init_db()
    yield db_file

    # Cleanup: close connection
    if hasattr(db_mod._local, "conn") and db_mod._local.conn is not None:
        try:
            db_mod._local.conn.close()
        except Exception:
            pass
        db_mod._local.conn = None


def _make_history_df(days=252, base_price=150.0, ticker="AAPL"):
    """Generate a realistic OHLCV DataFrame mimicking yfinance output."""
    import numpy as np

    dates = pd.bdate_range(end=datetime.now(), periods=days)
    np.random.seed(42)
    prices = base_price + np.cumsum(np.random.randn(days) * 2)
    prices = np.maximum(prices, 10)  # keep positive

    df = pd.DataFrame(
        {
            "Open": prices * 0.998,
            "High": prices * 1.01,
            "Low": prices * 0.99,
            "Close": prices,
            "Volume": (np.random.rand(days) * 50_000_000 + 10_000_000).astype(int),
        },
        index=dates,
    )
    return df


@pytest.fixture()
def mock_yfinance():
    """Patch yfinance.Ticker and yfinance.download with realistic mock data."""
    hist_df = _make_history_df()

    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = hist_df
    mock_ticker_instance.info = {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones.",
        "marketCap": 3_000_000_000_000,
        "exchange": "NMS",
    }

    # Build multi-ticker download DataFrame
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
    dfs = {}
    for t in tickers:
        dfs[t] = _make_history_df(days=5, base_price={"AAPL": 190, "MSFT": 420, "GOOGL": 175, "TSLA": 250, "NVDA": 900}.get(t, 150))

    # MultiIndex columns for group_by="ticker"
    arrays = []
    for t in tickers:
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            arrays.append((t, col))
    multi_idx = pd.MultiIndex.from_tuples(arrays)
    combined_data = pd.concat([dfs[t] for t in tickers], axis=1)
    combined_data.columns = multi_idx

    with patch("yfinance.Ticker", return_value=mock_ticker_instance) as mock_cls, \
         patch("yfinance.download", return_value=combined_data) as mock_dl:
        yield {
            "Ticker": mock_cls,
            "download": mock_dl,
            "instance": mock_ticker_instance,
            "hist_df": hist_df,
            "combined_data": combined_data,
        }
