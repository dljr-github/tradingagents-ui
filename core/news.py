"""News feed module: fetch headlines from Finviz and Yahoo Finance RSS."""

import logging
import re
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Cache: {ticker: (timestamp, results)}
_news_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 900  # 15 minutes

# Simple sentiment keyword lists
_BULLISH_WORDS = {
    "upgrade", "upgrades", "upgraded", "buy", "outperform", "overweight",
    "beat", "beats", "record", "surge", "surges", "soar", "soars", "rally",
    "rallies", "bullish", "boost", "boosts", "gain", "gains", "positive",
    "growth", "profit", "strong", "breakout", "high", "highs", "raised",
    "raises", "exceeds", "exceeded", "optimistic", "rebound", "rebounds",
}

_BEARISH_WORDS = {
    "downgrade", "downgrades", "downgraded", "sell", "underperform",
    "underweight", "miss", "misses", "missed", "drop", "drops", "fall",
    "falls", "crash", "crashes", "plunge", "plunges", "bearish", "decline",
    "declines", "loss", "losses", "weak", "low", "lows", "cut", "cuts",
    "warning", "warns", "negative", "risk", "lawsuit", "investigation",
    "recall", "fraud", "bankruptcy", "layoff", "layoffs",
}


def _sentiment_hint(title: str) -> str:
    """Scan title for bullish/bearish keywords and return a sentiment hint."""
    words = set(re.findall(r"[a-z]+", title.lower()))
    bull_count = len(words & _BULLISH_WORDS)
    bear_count = len(words & _BEARISH_WORDS)
    if bull_count > bear_count:
        return "bullish"
    elif bear_count > bull_count:
        return "bearish"
    return "neutral"


def _fetch_finviz(ticker: str) -> list[dict]:
    """Scrape news headlines from Finviz quote page."""
    import requests
    from bs4 import BeautifulSoup

    url = f"https://finviz.com/quote.ashx?t={ticker.upper()}"
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Finviz fetch failed for %s: %s", ticker, e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    news_table = soup.find("table", {"id": "news-table"})
    if not news_table:
        return []

    results = []
    current_date = ""
    for row in news_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        date_cell = cells[0].text.strip()
        link_tag = cells[1].find("a")
        if not link_tag:
            continue

        title = link_tag.text.strip()
        url = link_tag.get("href", "")
        source_span = cells[1].find("span")
        source = source_span.text.strip() if source_span else "Finviz"

        # Parse date: either "Mon-DD-YY HH:MM" or just "HH:MMAM/PM"
        if len(date_cell) > 8:
            current_date = date_cell.split()[0] if " " in date_cell else date_cell
            published = date_cell
        else:
            published = f"{current_date} {date_cell}" if current_date else date_cell

        results.append({
            "title": title,
            "url": url,
            "source": source,
            "published": published,
            "sentiment_hint": _sentiment_hint(title),
        })

    return results


def _fetch_yahoo_rss(ticker: str) -> list[dict]:
    """Fetch news from Yahoo Finance RSS feed as fallback."""
    import feedparser

    feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker.upper()}&region=US&lang=en-US"
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        logger.warning("Yahoo RSS fetch failed for %s: %s", ticker, e)
        return []

    results = []
    for entry in feed.entries[:20]:
        published = ""
        if hasattr(entry, "published"):
            published = entry.published
        elif hasattr(entry, "updated"):
            published = entry.updated

        title = entry.get("title", "")
        results.append({
            "title": title,
            "url": entry.get("link", ""),
            "source": "Yahoo Finance",
            "published": published,
            "sentiment_hint": _sentiment_hint(title),
        })

    return results


def get_news(ticker: str, max_items: int = 20) -> list[dict]:
    """Get news headlines for a ticker. Uses cache (15 min TTL).

    Tries Finviz first, falls back to Yahoo Finance RSS.
    Returns list of dicts with keys: title, url, source, published, sentiment_hint.
    """
    ticker = ticker.upper()
    now = time.time()

    # Check cache
    if ticker in _news_cache:
        cached_time, cached_results = _news_cache[ticker]
        if now - cached_time < _CACHE_TTL:
            return cached_results[:max_items]

    # Try Finviz first
    results = _fetch_finviz(ticker)

    # Fallback to Yahoo RSS
    if not results:
        results = _fetch_yahoo_rss(ticker)

    # Cache results
    _news_cache[ticker] = (now, results)
    return results[:max_items]


def clear_news_cache(ticker: Optional[str] = None):
    """Clear news cache for a specific ticker or all tickers."""
    if ticker:
        _news_cache.pop(ticker.upper(), None)
    else:
        _news_cache.clear()
