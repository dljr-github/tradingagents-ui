"""Stock screener data via yfinance."""

import logging
from functools import lru_cache
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Representative S&P 500 sector ETFs
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Disc.": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication": "XLC",
}

# Popular tickers for top movers scanning
SCAN_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "JNJ", "UNH", "XOM", "PG", "MA", "HD", "CVX", "MRK",
    "ABBV", "PEP", "KO", "COST", "AVGO", "LLY", "WMT", "MCD", "CSCO",
    "ACN", "TMO", "DHR", "ABT", "NEE", "LIN", "TXN", "PM", "UNP",
    "RTX", "LOW", "HON", "AMGN", "IBM", "BA", "CAT", "GS", "SPGI",
    "AMD", "INTC", "QCOM", "AMAT",
]


def get_ticker_info(ticker: str) -> dict:
    """Get company name, sector, industry, and description for a ticker."""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        return {
            "name": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "description": info.get("longBusinessSummary", ""),
            "market_cap": info.get("marketCap"),
            "exchange": info.get("exchange", ""),
        }
    except Exception as e:
        logger.warning("Failed to get info for %s: %s", ticker, e)
        return {"name": ticker, "sector": "", "industry": "", "description": ""}


# Cache ticker info to avoid repeated API calls
_ticker_info_cache: dict[str, dict] = {}


def get_ticker_info_cached(ticker: str) -> dict:
    """Cached version of get_ticker_info."""
    if ticker not in _ticker_info_cache:
        _ticker_info_cache[ticker] = get_ticker_info(ticker)
    return _ticker_info_cache[ticker]


def get_quick_stats(ticker: str) -> dict:
    """Get price, change, volume, RSI, 50/200 SMA for a single ticker."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if hist.empty:
            return {"ticker": ticker, "error": "No data"}

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        price = latest["Close"]
        change_pct = ((price - prev["Close"]) / prev["Close"]) * 100

        # RSI (14-period)
        delta = hist["Close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi_series = 100 - (100 / (1 + rs))
        rsi = rsi_series.iloc[-1] if not rsi_series.empty else None

        sma50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else None
        sma200 = hist["Close"].rolling(200).mean().iloc[-1] if len(hist) >= 200 else None

        # Get company info
        info = get_ticker_info_cached(ticker)

        return {
            "ticker": ticker,
            "name": info.get("name", ticker),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(latest["Volume"]),
            "rsi": round(rsi, 1) if rsi and pd.notna(rsi) else None,
            "sma50": round(sma50, 2) if sma50 and pd.notna(sma50) else None,
            "sma200": round(sma200, 2) if sma200 and pd.notna(sma200) else None,
        }
    except Exception as e:
        logger.warning("Failed to get stats for %s: %s", ticker, e)
        return {"ticker": ticker, "error": str(e)}


def get_top_movers(n: int = 10) -> dict:
    """Get top gainers, losers, and volume movers from scan universe."""
    results = []
    tickers_str = " ".join(SCAN_UNIVERSE)
    try:
        data = yf.download(tickers_str, period="5d", group_by="ticker", progress=False, threads=True)
    except Exception:
        data = pd.DataFrame()

    for ticker in SCAN_UNIVERSE:
        try:
            if len(SCAN_UNIVERSE) > 1 and ticker in data.columns.get_level_values(0):
                df = data[ticker].dropna()
            else:
                df = data.dropna()
            if df.empty or len(df) < 2:
                continue
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            price = latest["Close"]
            change_pct = ((price - prev["Close"]) / prev["Close"]) * 100
            vol = latest["Volume"]
            avg_vol = df["Volume"].mean()
            vol_ratio = vol / avg_vol if avg_vol > 0 else 1
            info = get_ticker_info_cached(ticker)
            results.append({
                "ticker": ticker,
                "name": info.get("name", ticker),
                "sector": info.get("sector", ""),
                "price": round(float(price), 2),
                "change_pct": round(float(change_pct), 2),
                "volume": int(vol),
                "vol_ratio": round(float(vol_ratio), 2),
            })
        except Exception:
            continue

    if not results:
        return {"gainers": [], "losers": [], "volume": []}

    df_results = pd.DataFrame(results)
    gainers = df_results.nlargest(n, "change_pct").to_dict("records")
    losers = df_results.nsmallest(n, "change_pct").to_dict("records")
    volume = df_results.nlargest(n, "vol_ratio").to_dict("records")
    return {"gainers": gainers, "losers": losers, "volume": volume}


def get_sector_performance() -> list[dict]:
    """Get daily performance for S&P 500 sector ETFs."""
    results = []
    tickers_str = " ".join(SECTOR_ETFS.values())
    try:
        data = yf.download(tickers_str, period="5d", group_by="ticker", progress=False, threads=True)
    except Exception:
        return results

    for sector, etf in SECTOR_ETFS.items():
        try:
            if etf in data.columns.get_level_values(0):
                df = data[etf].dropna()
            else:
                continue
            if df.empty or len(df) < 2:
                continue
            latest = df.iloc[-1]["Close"]
            prev = df.iloc[-2]["Close"]
            change_pct = ((latest - prev) / prev) * 100
            results.append({
                "sector": sector,
                "etf": etf,
                "change_pct": round(float(change_pct), 2),
            })
        except Exception:
            continue
    return sorted(results, key=lambda x: x["change_pct"], reverse=True)


def get_ticker_price(ticker: str) -> float | None:
    """Get the latest closing price for a ticker."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="5d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None
