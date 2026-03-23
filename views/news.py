"""News Feed page — ticker news headlines with sentiment indicators."""

from datetime import datetime, timezone

import streamlit as st
from core.database import get_watchlist
from core.news import get_news
from views.icons import icon, page_header


def _time_ago(published: str) -> str:
    """Convert a published timestamp to a human-readable 'time ago' string."""
    if not published:
        return ""
    try:
        # Try ISO format first
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
    except (ValueError, TypeError):
        return published

    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    return f"{days // 7}w ago"


def _sentiment_dot(hint: str) -> str:
    """Return an HTML dot colored by sentiment."""
    colors = {
        "bullish": "var(--green)",
        "positive": "var(--green)",
        "bearish": "var(--red)",
        "negative": "var(--red)",
        "neutral": "var(--text-muted)",
    }
    color = colors.get(hint, "var(--text-muted)")
    return (
        f'<span style="display:inline-block; width:8px; height:8px; '
        f'border-radius:50%; background:{color}; margin-right:6px; '
        f'vertical-align:middle;"></span>'
    )


def _render_news_list(articles: list[dict]):
    """Render a list of news articles."""
    if not articles:
        st.info("No news articles found.")
        return

    for article in articles:
        title = article.get("title", "Untitled")
        url = article.get("url", "")
        source = article.get("source", "Unknown")
        published = article.get("published", "")
        sentiment = article.get("sentiment_hint", "neutral")

        time_str = _time_ago(published)
        dot = _sentiment_dot(sentiment)

        link_html = f'<a href="{url}" target="_blank" rel="noopener" style="color:var(--text-primary); text-decoration:none; font-weight:500; font-size:0.92rem;">{title}</a>' if url else f'<span style="color:var(--text-primary); font-weight:500; font-size:0.92rem;">{title}</span>'

        st.markdown(f"""
        <div style="display:flex; align-items:flex-start; gap:10px; padding:12px 16px;
                    border-bottom:1px solid var(--border-subtle); transition:var(--transition);">
            <div style="padding-top:4px;">{dot}</div>
            <div style="flex:1; min-width:0;">
                <div>{link_html}</div>
                <div style="display:flex; align-items:center; gap:10px; margin-top:6px;">
                    <span style="font-family:var(--font-ui); font-size:0.75rem; font-weight:600;
                                 color:var(--cyan); background:var(--cyan-dim); padding:2px 8px;
                                 border-radius:4px; text-transform:uppercase; letter-spacing:0.04em;">
                        {source}
                    </span>
                    <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">
                        {time_str}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render():
    st.markdown(page_header("newspaper", "News Feed", "Market Headlines & Sentiment"), unsafe_allow_html=True)

    # Ticker lookup
    col1, col2 = st.columns([4, 1])
    with col1:
        lookup_ticker = st.text_input(
            "Look up ticker", placeholder="e.g. AAPL", key="news_lookup"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        lookup_btn = st.button("Get News", use_container_width=True)

    # Show news for looked-up ticker
    if lookup_btn and lookup_ticker:
        ticker = lookup_ticker.strip().upper()
        with st.spinner(f"Fetching news for {ticker}..."):
            articles = get_news(ticker)
        st.markdown(
            f'<div style="font-family:var(--font-mono); font-weight:700; font-size:1.1rem; '
            f'color:var(--text-primary); margin:16px 0 8px 0;">{ticker} Headlines</div>',
            unsafe_allow_html=True,
        )
        _render_news_list(articles)

    st.divider()

    # Watchlist news
    wl = get_watchlist()
    if wl:
        st.markdown(
            '<div style="font-family:var(--font-ui); font-weight:600; font-size:1rem; '
            'color:var(--text-primary); margin-bottom:12px;">Watchlist News</div>',
            unsafe_allow_html=True,
        )

        tabs = st.tabs([item["ticker"] for item in wl])
        for i, item in enumerate(wl):
            with tabs[i]:
                with st.spinner(f"Loading {item['ticker']}..."):
                    articles = get_news(item["ticker"])
                _render_news_list(articles)
    else:
        st.caption("Add tickers to your watchlist to see their news here automatically.")
