"""Comparison page — side-by-side ticker analysis and charts."""

import streamlit as st
from core.screener_data import get_quick_stats, get_price_history, get_ticker_info_cached
from views.icons import page_header


def render():
    st.markdown(page_header("columns", "Comparison", "Side-by-Side Ticker Analysis"), unsafe_allow_html=True)

    # Multi-select for tickers
    tickers_input = st.multiselect(
        "Select tickers to compare (2-3)",
        options=[],
        default=[],
        max_selections=3,
        key="compare_tickers",
        placeholder="Type ticker symbols...",
    )

    # Also allow text input for flexibility
    ticker_text = st.text_input(
        "Or enter tickers separated by commas",
        placeholder="e.g. AAPL, MSFT, GOOGL",
        key="compare_text",
    )

    tickers = []
    if ticker_text:
        tickers = [t.strip().upper() for t in ticker_text.split(",") if t.strip()]
    elif tickers_input:
        tickers = [t.upper() for t in tickers_input]

    if len(tickers) < 2:
        st.caption("Enter at least 2 tickers to compare.")
        return

    tickers = tickers[:3]  # Max 3

    # Fetch stats for all tickers
    all_stats = {}
    with st.spinner("Fetching data..."):
        for t in tickers:
            all_stats[t] = get_quick_stats(t)

    # Check for errors
    valid_tickers = [t for t in tickers if "error" not in all_stats[t]]
    if len(valid_tickers) < 2:
        st.error("Could not fetch data for enough tickers. Please check the symbols.")
        return

    # Side-by-side stats cards
    _render_stats_cards(valid_tickers, all_stats)

    st.divider()

    # Overlaid price chart
    _render_price_chart(valid_tickers)

    st.divider()

    # Comparison table
    _render_comparison_table(valid_tickers, all_stats)


def _render_stats_cards(tickers: list[str], all_stats: dict):
    cols = st.columns(len(tickers))
    for i, ticker in enumerate(tickers):
        stats = all_stats[ticker]
        info = get_ticker_info_cached(ticker)
        name = info.get("name", ticker)
        change = stats.get("change_pct", 0)
        delta_cls = "positive" if change > 0 else "negative" if change < 0 else ""
        sign = "+" if change > 0 else ""

        with cols[i]:
            st.markdown(f"""
            <div class="ta-card" style="text-align:center; padding:20px;">
                <div class="card-ticker" style="font-size:1.2rem;">{ticker}</div>
                <div style="color:var(--text-secondary); font-size:0.82rem; margin:4px 0 12px 0;">{name}</div>
                <div class="card-value" style="font-size:1.4rem;">${stats.get('price', 0):,.2f}</div>
                <div class="stat-delta {delta_cls}" style="margin-top:4px;">{sign}{change:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)


def _render_price_chart(tickers: list[str]):
    import plotly.graph_objects as go

    st.markdown(
        '<div style="font-family:var(--font-ui); font-weight:600; font-size:1rem; '
        'color:var(--text-primary); margin-bottom:8px;">Normalized Price Comparison (% Change)</div>',
        unsafe_allow_html=True,
    )

    period = st.selectbox(
        "Period", ["3mo", "6mo", "1y", "2y"], index=2, key="compare_period"
    )

    colors = ["#00d26a", "#00b4d8", "#ffd700"]
    fig = go.Figure()

    for i, ticker in enumerate(tickers):
        hist = get_price_history(ticker, period)
        if hist.empty or len(hist) < 2:
            continue

        # Normalize to % change from start
        close = hist["Close"]
        start_price = float(close.iloc[0])
        if start_price == 0:
            continue
        pct_change = ((close - start_price) / start_price) * 100

        fig.add_trace(go.Scatter(
            x=hist.index,
            y=pct_change,
            mode="lines",
            name=ticker,
            line=dict(color=colors[i % len(colors)], width=2),
        ))

    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#8b95a5", family="DM Sans, sans-serif"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, font=dict(size=11),
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            title="% Change",
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.15)",
            side="right",
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_comparison_table(tickers: list[str], all_stats: dict):
    st.markdown(
        '<div style="font-family:var(--font-ui); font-weight:600; font-size:1rem; '
        'color:var(--text-primary); margin-bottom:8px;">Detailed Comparison</div>',
        unsafe_allow_html=True,
    )

    metrics = [
        ("Price", lambda s: f"${s.get('price', 0):,.2f}"),
        ("Change %", lambda s: f"{s.get('change_pct', 0):+.2f}%"),
        ("RSI (14)", lambda s: f"{s['rsi']:.1f}" if s.get('rsi') else "N/A"),
        ("Volume", lambda s: f"{s.get('volume', 0):,.0f}" if s.get('volume') else "N/A"),
        ("SMA 50", lambda s: f"${s['sma50']:,.2f}" if s.get('sma50') else "N/A"),
        ("SMA 200", lambda s: f"${s['sma200']:,.2f}" if s.get('sma200') else "N/A"),
    ]

    # Add market cap from ticker info
    for ticker in tickers:
        info = get_ticker_info_cached(ticker)
        all_stats[ticker]["_market_cap"] = info.get("market_cap")

    metrics.append(("Market Cap", lambda s: _format_market_cap(s.get("_market_cap"))))

    # Build HTML table
    header_cells = '<th style="text-align:left; padding:8px 12px; color:var(--text-muted); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; border-bottom:1px solid var(--border-medium);">Metric</th>'
    for ticker in tickers:
        header_cells += f'<th style="text-align:right; padding:8px 12px; color:var(--text-primary); font-family:var(--font-mono); font-weight:700; font-size:0.95rem; border-bottom:1px solid var(--border-medium);">{ticker}</th>'

    rows_html = ""
    for metric_name, fmt_fn in metrics:
        cells = f'<td style="padding:10px 12px; color:var(--text-secondary); font-size:0.85rem; border-bottom:1px solid var(--border-subtle);">{metric_name}</td>'
        for ticker in tickers:
            stats = all_stats[ticker]
            value = fmt_fn(stats)

            # Color code change %
            style = "font-family:var(--font-mono); font-size:0.9rem;"
            if metric_name == "Change %":
                change = stats.get("change_pct", 0)
                color = "var(--green)" if change > 0 else "var(--red)" if change < 0 else "var(--text-secondary)"
                style += f" color:{color}; font-weight:600;"
            else:
                style += " color:var(--text-primary);"

            cells += f'<td style="text-align:right; padding:10px 12px; {style} border-bottom:1px solid var(--border-subtle);">{value}</td>'
        rows_html += f"<tr>{cells}</tr>"

    st.markdown(f"""
    <div style="background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-md); overflow:hidden;">
        <table style="width:100%; border-collapse:collapse;">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


def _format_market_cap(value) -> str:
    """Format market cap into human-readable string."""
    if value is None:
        return "N/A"
    value = float(value)
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    elif value >= 1e9:
        return f"${value / 1e9:.2f}B"
    elif value >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:,.0f}"
