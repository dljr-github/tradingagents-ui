"""Earnings calendar: upcoming earnings dates via yfinance."""

import logging
from datetime import datetime, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)


def get_upcoming_earnings(tickers: list[str]) -> list[dict]:
    """Get upcoming earnings dates for a list of tickers.

    Returns list of dicts with: ticker, earnings_date, days_until
    Sorted by earnings_date ascending.
    """
    results = []
    today = datetime.now().date()

    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker.upper())
            cal = tk.calendar
            if cal is None or cal.empty:
                continue

            # yfinance calendar returns a DataFrame or dict depending on version
            earnings_date = None
            if hasattr(cal, "loc"):
                # DataFrame format
                if "Earnings Date" in cal.index:
                    val = cal.loc["Earnings Date"]
                    if hasattr(val, "iloc"):
                        val = val.iloc[0]
                    if hasattr(val, "date"):
                        earnings_date = val.date()
                    elif isinstance(val, str):
                        earnings_date = datetime.strptime(val, "%Y-%m-%d").date()
            elif isinstance(cal, dict):
                ed = cal.get("Earnings Date")
                if ed:
                    if isinstance(ed, list) and ed:
                        ed = ed[0]
                    if hasattr(ed, "date"):
                        earnings_date = ed.date()
                    elif isinstance(ed, str):
                        earnings_date = datetime.strptime(ed, "%Y-%m-%d").date()

            if earnings_date is None:
                continue

            days_until = (earnings_date - today).days
            if days_until < 0:
                continue  # Skip past earnings

            results.append({
                "ticker": ticker.upper(),
                "earnings_date": earnings_date.isoformat(),
                "days_until": days_until,
            })
        except Exception as e:
            logger.debug("Could not get earnings for %s: %s", ticker, e)
            continue

    results.sort(key=lambda x: x["days_until"])
    return results


def get_watchlist_earnings_flags(tickers: list[str], within_days: int = 14) -> list[dict]:
    """Flag watchlist items with earnings within N days.

    Returns only tickers with upcoming earnings within the threshold.
    """
    upcoming = get_upcoming_earnings(tickers)
    return [e for e in upcoming if e["days_until"] <= within_days]
